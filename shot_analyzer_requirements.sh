# Badminton Shot Classification & Coaching System - Dependencies Setup
# Run these commands to install all required dependencies

echo "🏸 Setting up Badminton Shot Classification & Coaching System 🏸"
echo "=================================================================="

# Core computer vision and ML libraries
echo "📦 Installing computer vision libraries..."
pip3 install opencv-python
pip3 install mediapipe

# YOLO for object detection
echo "🎯 Installing YOLO for shuttlecock detection..."
pip3 install ultralytics

# Core ML frameworks
echo "🧠 Installing machine learning frameworks..."
pip3 install torch torchvision torchaudio
pip3 install numpy
pip3 install scikit-learn

# Data analysis and visualization
echo "📊 Installing data analysis libraries..."
pip3 install pandas
pip3 install matplotlib
pip3 install seaborn

# Utilities
echo "🔧 Installing utility libraries..."
pip3 install pathlib2
pip3 install tqdm

# Optional performance improvements
echo "⚡ Installing performance optimization libraries..."
pip3 install numba  # For faster numerical computations

# Verify installations
echo "✅ Verifying installations..."
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import mediapipe as mp; print('MediaPipe: ✅')"
python -c "import ultralytics; print('YOLO/Ultralytics: ✅')"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"

echo ""
echo "🎉 Setup complete!"
echo "📋 Next steps:"
echo "   1. Run: python badminton_shot_analyzer.py your_video.mp4"
echo "   2. First run will download YOLO model (~6MB)"
echo "   3. Enjoy real-time badminton shot analysis!"
