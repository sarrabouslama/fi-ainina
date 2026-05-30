import cv2
import time

def test_default():
    print("Testing default index 0...")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("Camera 0 opened successfully!")
        ret, frame = cap.read()
        if ret:
            print("Frame read successfully!")
        else:
            print("Failed to read frame.")
        cap.release()
    else:
        print("Failed to open Camera 0.")

if __name__ == "__main__":
    test_default()
