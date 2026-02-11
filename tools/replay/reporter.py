"""Print summary and optionally save results to JSON."""

import json
import logging
from typing import Optional

from .sender import FrameSender

logger = logging.getLogger(__name__)


class ResultReporter:
    def __init__(self, sender: FrameSender):
        self.sender = sender

    def print_summary(self):
        s = self.sender
        print("\n--- Replay Summary ---")
        print(f"  Frames sent:   {s.frames_sent}")
        print(f"  Results recv:  {len(s.results)}")
        print(f"  Elapsed:       {s.elapsed:.1f}s")
        print(f"  Effective FPS: {s.effective_fps:.1f}")

        if s.final_report:
            print("\n--- Final Report ---")
            summary = s.final_report.get("summary", s.final_report)
            for k, v in summary.items():
                if not isinstance(v, (dict, list)):
                    print(f"  {k}: {v}")
            dist = s.final_report.get("shot_distribution", {})
            if dist:
                print(f"  shot_distribution: {json.dumps(dist)}")
        else:
            print("  (No final report received)")

    def save_json(self, path: str):
        s = self.sender
        data = {
            "summary": {
                "frames_sent": s.frames_sent,
                "results_received": len(s.results),
                "elapsed_seconds": round(s.elapsed, 2),
                "effective_fps": round(s.effective_fps, 2),
            },
            "final_report": s.final_report,
            "results": s.results,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Results saved to {path}")
