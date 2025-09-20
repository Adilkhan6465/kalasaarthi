from google.cloud import vision
from PIL import Image
import io
import numpy as np
import cv2

def analyze_image_bytes(image_bytes: bytes):
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)

    labels_resp = client.label_detection(image=image, max_results=8)
    labels = [l.description for l in labels_resp.label_annotations]

    props = client.image_properties(image=image).image_properties_annotation
    colors = []
    if props and props.dominant_colors and props.dominant_colors.colors:
        for c in props.dominant_colors.colors[:3]:
            colors.append({
                "fraction": c.pixel_fraction,
                "rgb": (int(c.color.red or 0), int(c.color.green or 0), int(c.color.blue or 0))
            })

    # Local brightness & sharpness check
    pil = Image.open(io.BytesIO(image_bytes)).convert("L")
    arr = np.array(pil)
    mean_brightness = float(arr.mean())
    fm = float(cv2.Laplacian(arr, cv2.CV_64F).var())

    feedback = []
    if mean_brightness < 60:
        feedback.append("Image looks dark — increase lighting.")
    elif mean_brightness > 200:
        feedback.append("Image too bright — adjust lighting.")
    if fm < 100:
        feedback.append("Image may be blurry — use steady hands.")
    if any(lbl.lower() in ["clutter", "indoor", "room", "background"] for lbl in labels):
        feedback.append("Use plain background to highlight the product.")

    return {
        "labels": labels,
        "dominant_colors": colors,
        "mean_brightness": mean_brightness,
        "sharpness_score": fm,
        "feedback": feedback
    }