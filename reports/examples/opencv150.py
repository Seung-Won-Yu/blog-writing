"""Bright-paper candidate demo, not OCR or a production document scanner."""
import argparse
from pathlib import Path
import cv2
import numpy as np


def sample_image():
    image = np.full((480, 640, 3), 35, dtype=np.uint8)
    cv2.rectangle(image, (180, 80), (460, 400), (235, 235, 235), -1)
    for y in range(120, 350, 35):
        cv2.line(image, (210, y), (420, y), (60, 60, 60), 2)
    return image


def detect(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    threshold, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    height, width = gray.shape
    candidates = []
    for contour in contours:
        ratio = cv2.contourArea(contour) / (height * width)
        x, y, w, h = cv2.boundingRect(contour)
        touches_border = x == 0 or y == 0 or x + w >= width or y + h >= height
        polygon = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if 0.10 <= ratio <= 0.90 and not touches_border:
            if len(polygon) == 4 and cv2.isContourConvex(polygon):
                candidates.append((cv2.contourArea(contour), polygon))
    result = image.copy()
    if candidates:
        _, polygon = max(candidates, key=lambda item: item[0])
        cv2.polylines(result, [polygon], True, (0, 180, 0), 3)
    return threshold, candidates, (gray, blurred, binary, closed, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("opencv150-output"))
    args = parser.parse_args()
    image = sample_image()
    if args.input is not None:
        data = np.frombuffer(args.input.read_bytes(), dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
        if image is None:
            raise ValueError(f"Cannot decode image: {args.input}")
    threshold, candidates, steps = detect(image)
    args.out.mkdir(parents=True, exist_ok=False)
    names = ["01-gray", "02-blur", "03-binary", "04-closed", "05-result"]
    for name, step in zip(["00-input"] + names, [image] + list(steps)):
        ok, encoded = cv2.imencode(".png", step)
        if not ok:
            raise OSError(f"Encoding failed: {name}")
        (args.out / f"{name}.png").write_bytes(encoded.tobytes())
    print(f"shape={image.shape}, dtype={image.dtype}")
    print(f"threshold={threshold:.1f}, candidates={len(candidates)}")
    print("candidate found" if candidates else "NO CANDIDATE: inspect intermediate images")
    print(f"saved 6 PNG files: {args.out.resolve()}")


if __name__ == "__main__":
    main()
