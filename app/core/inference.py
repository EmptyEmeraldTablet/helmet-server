from pathlib import Path
from time import perf_counter

import cv2
from app.config import settings


class InferenceEngine:
    def __init__(self, weights_path: str, confidence: float) -> None:
        from ultralytics import YOLO

        weights = Path(weights_path)
        if not weights.exists():
            raise FileNotFoundError(f"Weights not found: {weights_path}")
        self.model = YOLO(weights_path)
        self.confidence = confidence

    def predict(self, image_path: str) -> tuple[list[dict], float, str | None]:
        start = perf_counter()
        results = self.model.predict(image_path, conf=self.confidence)
        elapsed_ms = (perf_counter() - start) * 1000

        detections: list[dict] = []
        annotated_path: str | None = None

        if results:
            result = results[0]
            names = result.names
            for box in result.boxes:
                label = names.get(int(box.cls[0]), "unknown")
                detections.append(
                    {
                        "label": label,
                        "confidence": float(box.conf[0]),
                        "bbox": [float(v) for v in box.xyxy[0].tolist()],
                    }
                )
            if result.boxes is not None:
                annotated = result.plot()
                annotated_path = str(Path(settings.annotated_dir) / Path(image_path).name)
                cv2.imwrite(annotated_path, annotated)

        return detections, elapsed_ms, annotated_path


_engine: InferenceEngine | None = None


def get_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        _engine = InferenceEngine(settings.weights_path, settings.inference_confidence)
    return _engine
