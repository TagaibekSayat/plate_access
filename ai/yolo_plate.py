import torch
from ultralytics import YOLO
import os

MODEL_PATH = os.path.join("models", "best_plate.pt")

device = 0 if torch.cuda.is_available() else "cpu"
print("Yolo device:",device)

model = YOLO(MODEL_PATH)
if device != "cpu":
    model.to("cuda")


def detect_plate_regions(frame, return_boxes=False):
    results = model(frame, imgsz=640, conf=0.4, device=device, verbose=False)

    plates = []
    h, w = frame.shape[:2]

    for r in results:
        for box in r.boxes.xyxy:
            x1, y1, x2, y2 = map(int, box.tolist())
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            if x2 <= x1 or y2 <= y1:
                continue

            plate = frame[y1:y2, x1:x2]
            if return_boxes:
                plates.append((plate, (x1, y1, x2, y2)))
            else:
                plates.append(plate)

    return plates
