import cv2

def list_cameras():
    print("Testing cameras...")
    for i in range(5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            print(f"Camera {i} is available with DSHOW")
            cap.release()
        else:
            print(f"Camera {i} is NOT available with DSHOW")
        
        cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
        if cap.isOpened():
            print(f"Camera {i} is available with MSMF")
            cap.release()
        else:
            print(f"Camera {i} is NOT available with MSMF")

if __name__ == "__main__":
    list_cameras()
