"""
Heatmap Visualizer - Multiple visualization styles for player movement data
===========================================================================
Load heatmap data JSON and create different visualization types:
- Rally-colored heatmaps (each rally different color)
- Trajectory/connected plots
- Overlapping rally comparison
- Time-based color gradient
"""

import json
import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class VisualizerConfig:
    """Configuration for visualizations"""
    output_width: int = 800
    output_height: int = 600
    background_color: tuple = (20, 20, 20)
    line_thickness: int = 2
    point_radius: int = 3


class HeatmapVisualizer:
    """Create different visualizations from foot position data"""

    # Distinct colors for rallies (BGR format)
    RALLY_COLORS = [
        (0, 255, 0),      # Green
        (0, 165, 255),    # Orange
        (255, 0, 255),    # Magenta
        (255, 255, 0),    # Cyan
        (0, 0, 255),      # Red
        (255, 0, 0),      # Blue
        (0, 255, 255),    # Yellow
        (128, 0, 128),    # Purple
        (0, 128, 255),    # Light orange
        (255, 128, 0),    # Light blue
    ]

    def __init__(self, data_path: str, config: VisualizerConfig = None, background_frame_path: str = None):
        self.config = config or VisualizerConfig()
        self.background_frame = None
        self.background_frame_path = background_frame_path

        # Load background frame if provided
        if background_frame_path and Path(background_frame_path).exists():
            self.background_frame = cv2.imread(background_frame_path)
            if self.background_frame is not None:
                # Update config dimensions to match background frame
                h, w = self.background_frame.shape[:2]
                self.config.output_width = w
                self.config.output_height = h

        with open(data_path, 'r') as f:
            self.data = json.load(f)

        self.positions = self.data['positions']
        self.rallies = self.data.get('rallies', [])
        self.court = self.data['metadata']['court_boundary']

        # Build perspective transform
        self._build_transform()

    def _build_transform(self):
        """Build perspective transform to normalize court coordinates"""
        src_points = np.array([
            self.court['top_left'],
            self.court['top_right'],
            self.court['bottom_right'],
            self.court['bottom_left']
        ], dtype=np.float32)

        margin = 20
        dst_points = np.array([
            [margin, margin],
            [self.config.output_width - margin, margin],
            [self.config.output_width - margin, self.config.output_height - margin],
            [margin, self.config.output_height - margin]
        ], dtype=np.float32)

        self.transform = cv2.getPerspectiveTransform(src_points, dst_points)
        # Flag to indicate if we're using real background (no transform needed)
        self.use_direct_coords = self.background_frame is not None

    def _transform_point(self, x: int, y: int, use_direct: bool = None) -> tuple:
        """Transform a single point to output coordinates"""
        # If using real background, return original coordinates
        if use_direct is None:
            use_direct = self.use_direct_coords
        if use_direct:
            return int(x), int(y)

        pt = np.array([[[x, y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, self.transform)
        return int(transformed[0, 0, 0]), int(transformed[0, 0, 1])

    def _create_canvas(self, use_background: bool = True, darken_factor: float = 0.5) -> np.ndarray:
        """Create canvas - uses background frame if available, otherwise plain color"""
        if use_background and self.background_frame is not None:
            # Use real video frame as background (darkened for better overlay visibility)
            canvas = self.background_frame.copy()
            # Darken the background for better visibility of overlays
            canvas = (canvas * darken_factor).astype(np.uint8)

            # Draw court boundary outline on the real frame
            court_pts = np.array([
                self.court['top_left'],
                self.court['top_right'],
                self.court['bottom_right'],
                self.court['bottom_left']
            ], dtype=np.int32)
            cv2.polylines(canvas, [court_pts], True, (100, 255, 100), 2)

            return canvas
        else:
            # Fallback to plain canvas
            canvas = np.full(
                (self.config.output_height, self.config.output_width, 3),
                self.config.background_color,
                dtype=np.uint8
            )

            # Draw court outline
            margin = 20
            court_pts = np.array([
                [margin, margin],
                [self.config.output_width - margin, margin],
                [self.config.output_width - margin, self.config.output_height - margin],
                [margin, self.config.output_height - margin]
            ], dtype=np.int32)
            cv2.polylines(canvas, [court_pts], True, (100, 100, 100), 1)

            # Center lines
            cv2.line(canvas,
                    (margin, self.config.output_height // 2),
                    (self.config.output_width - margin, self.config.output_height // 2),
                    (60, 60, 60), 1)
            cv2.line(canvas,
                    (self.config.output_width // 2, margin),
                    (self.config.output_width // 2, self.config.output_height - margin),
                    (60, 60, 60), 1)

            return canvas

    def _get_rally_positions(self, rally_id: int) -> List[dict]:
        """Get all positions for a specific rally"""
        return [p for p in self.positions if p['rally_id'] == rally_id]

    def create_rally_colored_heatmap(self, alpha: float = 0.6) -> np.ndarray:
        """
        Create heatmap where each rally has a different color.
        Overlapping areas show color mixing.
        """
        canvas = self._create_canvas()

        # Get unique rally IDs (excluding -1 which means between rallies)
        rally_ids = sorted(set(p['rally_id'] for p in self.positions if p['rally_id'] >= 0))

        if not rally_ids:
            # No rally data, use all positions with single color
            rally_ids = [-1]

        for idx, rally_id in enumerate(rally_ids):
            color = self.RALLY_COLORS[idx % len(self.RALLY_COLORS)]

            if rally_id == -1:
                positions = self.positions
            else:
                positions = self._get_rally_positions(rally_id)

            # Create overlay for this rally
            overlay = canvas.copy()

            for pos in positions:
                tx, ty = self._transform_point(pos['x'], pos['y'])
                cv2.circle(overlay, (tx, ty), self.config.point_radius + 2, color, -1)

            # Blend with main canvas
            cv2.addWeighted(overlay, alpha / len(rally_ids), canvas, 1 - alpha / len(rally_ids), 0, canvas)

        self._add_rally_legend(canvas, rally_ids)
        return canvas

    def create_trajectory_plot(self, show_points: bool = True,
                               connect_within_rally: bool = True) -> np.ndarray:
        """
        Create connected trajectory plot showing player movement paths.
        Each rally is a different color, with lines connecting consecutive positions.
        """
        canvas = self._create_canvas()

        rally_ids = sorted(set(p['rally_id'] for p in self.positions if p['rally_id'] >= 0))

        if not rally_ids:
            rally_ids = [0]
            # Treat all as one "rally"
            positions_by_rally = {0: self.positions}
        else:
            positions_by_rally = {rid: self._get_rally_positions(rid) for rid in rally_ids}

        for idx, rally_id in enumerate(rally_ids):
            color = self.RALLY_COLORS[idx % len(self.RALLY_COLORS)]
            positions = positions_by_rally.get(rally_id, self.positions if rally_id == 0 else [])

            # Sort by frame number
            positions = sorted(positions, key=lambda p: p['frame'])

            prev_point = None
            for pos in positions:
                tx, ty = self._transform_point(pos['x'], pos['y'])
                current_point = (tx, ty)

                # Draw line from previous point
                if connect_within_rally and prev_point:
                    cv2.line(canvas, prev_point, current_point, color, self.config.line_thickness)

                # Draw point
                if show_points:
                    cv2.circle(canvas, current_point, self.config.point_radius, color, -1)

                prev_point = current_point

        self._add_rally_legend(canvas, rally_ids)
        self._add_title(canvas, "Player Trajectory")
        return canvas

    def create_time_gradient_plot(self, colormap: int = cv2.COLORMAP_JET) -> np.ndarray:
        """
        Create plot where color represents time progression.
        Early positions are blue, late positions are red (with JET colormap).
        """
        canvas = self._create_canvas()

        if not self.positions:
            return canvas

        # Sort by timestamp
        sorted_positions = sorted(self.positions, key=lambda p: p['timestamp'])

        n_positions = len(sorted_positions)
        prev_point = None

        for i, pos in enumerate(sorted_positions):
            # Color based on time progression (0-255)
            color_val = int(i / n_positions * 255)
            color_img = cv2.applyColorMap(np.array([[color_val]], dtype=np.uint8), colormap)
            color = tuple(int(c) for c in color_img[0, 0])

            tx, ty = self._transform_point(pos['x'], pos['y'])
            current_point = (tx, ty)

            if prev_point:
                cv2.line(canvas, prev_point, current_point, color, 1)

            cv2.circle(canvas, current_point, 2, color, -1)
            prev_point = current_point

        # Add time legend
        self._add_time_legend(canvas, colormap)
        self._add_title(canvas, "Time Progression")
        return canvas

    def create_density_contour(self, levels: int = 10) -> np.ndarray:
        """
        Create contour-style density plot showing movement concentration.
        """
        canvas = self._create_canvas()

        if len(self.positions) < 10:
            return canvas

        # Create density grid
        grid_size = 50
        density = np.zeros((grid_size, grid_size), dtype=np.float32)

        for pos in self.positions:
            tx, ty = self._transform_point(pos['x'], pos['y'])
            # Map to grid
            gx = int(tx / self.config.output_width * (grid_size - 1))
            gy = int(ty / self.config.output_height * (grid_size - 1))
            gx = max(0, min(grid_size - 1, gx))
            gy = max(0, min(grid_size - 1, gy))
            density[gy, gx] += 1

        # Smooth
        density = cv2.GaussianBlur(density, (5, 5), 2)

        # Normalize and resize
        if density.max() > 0:
            density = (density / density.max() * 255).astype(np.uint8)

        density_resized = cv2.resize(density,
                                     (self.config.output_width, self.config.output_height),
                                     interpolation=cv2.INTER_CUBIC)

        # Find contours at different levels
        for level in range(1, levels + 1):
            threshold = int(level / levels * 255)
            _, binary = cv2.threshold(density_resized, threshold, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Color based on level (red = high, blue = low)
            color_val = int(level / levels * 255)
            color = cv2.applyColorMap(np.array([[color_val]], dtype=np.uint8), cv2.COLORMAP_HOT)[0, 0]
            color = tuple(int(c) for c in color)

            cv2.drawContours(canvas, contours, -1, color, 1)

        self._add_title(canvas, "Density Contours")
        return canvas

    def create_rally_comparison(self, rally_ids: List[int] = None) -> np.ndarray:
        """
        Create side-by-side or overlay comparison of specific rallies.
        If rally_ids is None, compares first 4 rallies.
        """
        all_rally_ids = sorted(set(p['rally_id'] for p in self.positions if p['rally_id'] >= 0))

        if not all_rally_ids:
            return self._create_canvas()

        if rally_ids is None:
            rally_ids = all_rally_ids[:4]
        else:
            rally_ids = [r for r in rally_ids if r in all_rally_ids]

        if not rally_ids:
            return self._create_canvas()

        n_rallies = len(rally_ids)

        # Create grid layout
        if n_rallies <= 2:
            rows, cols = 1, n_rallies
        else:
            rows, cols = 2, 2

        cell_w = self.config.output_width // cols
        cell_h = self.config.output_height // rows

        canvas = np.full(
            (self.config.output_height, self.config.output_width, 3),
            self.config.background_color,
            dtype=np.uint8
        )

        for idx, rally_id in enumerate(rally_ids[:4]):
            row = idx // cols
            col = idx % cols

            # Create mini canvas for this rally
            mini_config = VisualizerConfig(output_width=cell_w, output_height=cell_h)
            mini_canvas = np.full((cell_h, cell_w, 3), self.config.background_color, dtype=np.uint8)

            positions = self._get_rally_positions(rally_id)
            color = self.RALLY_COLORS[idx % len(self.RALLY_COLORS)]

            # Transform for mini canvas
            margin = 10
            src_points = np.array([
                self.court['top_left'],
                self.court['top_right'],
                self.court['bottom_right'],
                self.court['bottom_left']
            ], dtype=np.float32)

            dst_points = np.array([
                [margin, margin],
                [cell_w - margin, margin],
                [cell_w - margin, cell_h - margin],
                [margin, cell_h - margin]
            ], dtype=np.float32)

            mini_transform = cv2.getPerspectiveTransform(src_points, dst_points)

            # Draw trajectory
            positions = sorted(positions, key=lambda p: p['frame'])
            prev_point = None
            for pos in positions:
                pt = np.array([[[pos['x'], pos['y']]]], dtype=np.float32)
                transformed = cv2.perspectiveTransform(pt, mini_transform)
                tx, ty = int(transformed[0, 0, 0]), int(transformed[0, 0, 1])

                if prev_point:
                    cv2.line(mini_canvas, prev_point, (tx, ty), color, 1)
                cv2.circle(mini_canvas, (tx, ty), 2, color, -1)
                prev_point = (tx, ty)

            # Add rally label
            cv2.putText(mini_canvas, f"Rally {rally_id}", (5, 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            # Draw court outline
            court_pts = np.array([
                [margin, margin], [cell_w - margin, margin],
                [cell_w - margin, cell_h - margin], [margin, cell_h - margin]
            ], dtype=np.int32)
            cv2.polylines(mini_canvas, [court_pts], True, (80, 80, 80), 1)

            # Place in main canvas
            y_start = row * cell_h
            x_start = col * cell_w
            canvas[y_start:y_start + cell_h, x_start:x_start + cell_w] = mini_canvas

        return canvas

    def _add_rally_legend(self, canvas: np.ndarray, rally_ids: List[int]):
        """Add rally color legend to canvas"""
        x, y = self.config.output_width - 120, 20

        cv2.putText(canvas, "Rallies:", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        y += 20

        for idx, rally_id in enumerate(rally_ids[:8]):  # Max 8 in legend
            color = self.RALLY_COLORS[idx % len(self.RALLY_COLORS)]
            cv2.rectangle(canvas, (x, y - 8), (x + 12, y + 2), color, -1)
            label = f"Rally {rally_id}" if rally_id >= 0 else "Between"
            cv2.putText(canvas, label, (x + 18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
            y += 15

    def _add_time_legend(self, canvas: np.ndarray, colormap: int):
        """Add time progression legend"""
        x, y = 20, self.config.output_height - 40
        legend_width = 150

        # Draw gradient bar
        for i in range(legend_width):
            val = int(i / legend_width * 255)
            color = cv2.applyColorMap(np.array([[val]], dtype=np.uint8), colormap)[0, 0]
            cv2.line(canvas, (x + i, y), (x + i, y + 10), tuple(int(c) for c in color), 1)

        cv2.putText(canvas, "Start", (x, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
        cv2.putText(canvas, "End", (x + legend_width - 20, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

    def _add_title(self, canvas: np.ndarray, title: str):
        """Add title to canvas"""
        cv2.putText(canvas, title, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    def save_all_visualizations(self, output_dir: str = None):
        """Generate and save all visualization types"""
        if output_dir is None:
            output_dir = Path(self.data['metadata'].get('video_name', 'output'))
            output_dir = Path("analysis_output") / f"visualizations_{output_dir}"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        visualizations = {
            'rally_heatmap': self.create_rally_colored_heatmap(),
            'trajectory': self.create_trajectory_plot(),
            'time_gradient': self.create_time_gradient_plot(),
            'density_contour': self.create_density_contour(),
            'rally_comparison': self.create_rally_comparison(),
        }

        saved_paths = {}
        for name, image in visualizations.items():
            path = output_dir / f"{name}.png"
            cv2.imwrite(str(path), image)
            saved_paths[name] = str(path)
            print(f"Saved: {path}")

        return saved_paths


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python heatmap_visualizer.py <heatmap_data.json>")
        print("\nThis script creates multiple visualizations from foot position data:")
        print("  - rally_heatmap.png    : Each rally in different color")
        print("  - trajectory.png       : Connected movement paths")
        print("  - time_gradient.png    : Color shows time progression")
        print("  - density_contour.png  : Contour lines showing density")
        print("  - rally_comparison.png : Side-by-side rally comparison")
        return

    data_path = sys.argv[1]

    if not Path(data_path).exists():
        print(f"Error: File not found: {data_path}")
        return

    print(f"Loading data from: {data_path}")
    visualizer = HeatmapVisualizer(data_path)

    print(f"Loaded {len(visualizer.positions)} positions")
    print(f"Found {len(visualizer.rallies)} rallies")

    # Save all visualizations
    saved = visualizer.save_all_visualizations()

    print(f"\nGenerated {len(saved)} visualizations")


if __name__ == "__main__":
    main()
