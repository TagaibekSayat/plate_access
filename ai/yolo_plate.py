import torch
from ultralytics import YOLO
import os

MODEL_PATH = os.path.join("models", "best_plate.pt")

device = 0 if torch.cuda.is_available() else "cpu"
print("Yolo device:",device)

model = YOLO(MODEL_PATH)
if device != "cpu":
    model.to("cuda")


def detect_plate_regions(frame):
    results = model(frame, imgsz=640, conf=0.4, device=device, verbose=False)

    plates = []

    for r in results:
        for box in r.boxes.xyxy:
            x1, y1, x2, y2 = map(int, box.tolist())
            plate = frame[y1:y2, x1:x2]
            plates.append(plate)

    return plates
