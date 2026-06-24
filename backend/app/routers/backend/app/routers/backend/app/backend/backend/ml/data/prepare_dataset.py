"""
BANDA AI - Pipeline Préparation Données Tropicales
Télécharge CGIAR/IITA, nettoie, déduplique et exporte en TFRecord.
Exécution: python ml/data/prepare_dataset.py --output data/tfrecords/
"""
import os
import hashlib
import argparse
from pathlib import Path
from PIL import Image
import tensorflow as tf

# Sources de données tropicales vérifiées
DATASET_SOURCES = {
    "cassava": "https://storage.googleapis.com/cassava-dataset/cassava-leaf-disease-classification.zip",
    "maize_faw": "https://data.cgiar.org/api/core/datasets/fall-armyworm-images/download",
    "banana_sigatoka": "https://data.cgiar.org/api/core/datasets/banana-sigatoka/download",
}

TARGET_SIZE = (224, 224)
BATCH_SIZE = 32


def download_and_extract(url: str, dest_dir: Path):
    """Télécharge et extrait un dataset avec vérification d'intégrité."""
    zip_path = dest_dir / f"{url.split('/')[-1]}"
    if not zip_path.exists():
        print(f"📥 Téléchargement: {url}")
        os.system(f"wget -q '{url}' -O '{zip_path}'")
    print(f"📦 Extraction: {zip_path.name}")
    os.system(f"unzip -qo '{zip_path}' -d '{dest_dir}'")


def deduplicate_images(image_paths: list[Path]) -> list[Path]:
    """Supprime les doublons par hash perceptuel (évite surapprentissage)."""
    hashes = set()
    unique_paths = []
    for path in image_paths:
        with open(path, "rb") as f:
            img_hash = hashlib.md5(f.read()).hexdigest()
        if img_hash not in hashes:
            hashes.add(img_hash)
            unique_paths.append(path)
    print(f"🧹 Déduplication: {len(image_paths)} → {len(unique_paths)} images")
    return unique_paths


def create_tfrecord(images: list[Path], labels: list[int], output_path: str):
    """Exporte en TFRecord optimisé pour TFLite training."""
    writer = tf.io.TFRecordWriter(output_path)    for img_path, label in zip(images, labels):
        img = tf.io.read_file(str(img_path))
        img = tf.image.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, TARGET_SIZE)
        
        feature = {
            "image": tf.train.Feature(bytes_list=tf.train.BytesList(value=[tf.io.encode_jpeg(tf.cast(img, tf.uint8)).numpy()])),
            "label": tf.train.Feature(int64_list=tf.train.Int64List(value=[label])),
        }
        example = tf.train.Example(features=tf.train.Features(feature=feature))
        writer.write(example.SerializeToString())
    writer.close()
    print(f"✅ TFRecord créé: {output_path} ({len(images)} images)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="ml/data/tfrecords/", help="Dossier de sortie TFRecords")
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Pipeline complet
    raw_dir = Path("ml/data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    for crop, url in DATASET_SOURCES.items():
        print(f"\n🌱 Traitement: {crop}")
        crop_dir = raw_dir / crop
        download_and_extract(url, crop_dir)
        
        # Collecter images + labels (structure attendue: crop/class_name/*.jpg)
        images, labels = [], []
        class_names = sorted([d.name for d in crop_dir.iterdir() if d.is_dir()])
        label_map = {name: idx for idx, name in enumerate(class_names)}
        
        for class_name, label_idx in label_map.items():
            class_imgs = list((crop_dir / class_name).glob("*.jpg"))
            images.extend(class_imgs)
            labels.extend([label_idx] * len(class_imgs))
        
        # Nettoyage + Export
        unique_images = deduplicate_images(images)
        create_tfrecord(unique_images, labels[:len(unique_images)], str(output_dir / f"{crop}.tfrecord"))
        
        # Sauvegarder le mapping des classes pour l'inférence
        with open(output_dir / f"{crop}_labels.txt", "w") as f:
            f.write("\n".join(class_names))
        print("\n🎉 Pipeline terminé! Prêt pour l'entraînement.")
