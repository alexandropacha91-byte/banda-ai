"""
BANDA AI - Entraînement Modèle Tropical MobileNetV3
Fine-tuning avec augmentation de données spécifique aux feuilles tropicales.
"""
import tensorflow as tf
from pathlib import Path

TFRECORD_DIR = Path("ml/data/tfrecords/")
MODEL_OUTPUT = "ml/models/banda_v1.tflite"
EPOCHS = 20
BATCH_SIZE = 32


def load_tfrecord(file_pattern: str, num_classes: int):
    """Charge un TFRecord avec augmentation de données tropicale."""
    def parse_fn(example):
        features = tf.io.parse_single_example(example, {
            "image": tf.io.FixedLenFeature([], tf.string),
            "label": tf.io.FixedLenFeature([], tf.int64),
        })
        image = tf.io.decode_jpeg(features["image"], channels=3)
        image = tf.image.resize(image, [224, 224])
        image = tf.cast(image, tf.float32) / 255.0
        
        # Augmentation spécifique tropical (lumière forte, ombres portées)
        image = tf.image.random_brightness(image, 0.3)
        image = tf.image.random_contrast(image, 0.7, 1.3)
        image = tf.image.random_flip_left_right(image)
        
        label = tf.one_hot(features["label"], num_classes)
        return image, label
    
    dataset = tf.data.Dataset.list_files(file_pattern)
    dataset = dataset.interleave(
        lambda x: tf.data.TFRecordDataset(x),
        cycle_length=4, block_length=16
    )
    dataset = dataset.map(parse_fn, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.shuffle(1000).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    return dataset


def build_model(num_classes: int):
    """MobileNetV3Small + tête personnalisée anti-overfitting."""
    base = tf.keras.applications.MobileNetV3Small(
        input_shape=(224, 224, 3), include_top=False, weights="imagenet"
    )
    base.trainable = False  # Freeze backbone phase 1
    
    model = tf.keras.Sequential([
        base,
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dropout(0.4),  # Dropout élevé pour petits datasets
        tf.keras.layers.Dense(128, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ])
    return model


if __name__ == "__main__":
    # Charger données (exemple: cassava)
    train_ds = load_tfrecord(str(TFRECORD_DIR / "cassava.tfrecord"), num_classes=5)
    
    model = build_model(num_classes=5)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )
    
    # Callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=2),
    ]
    
    print("🚀 Démarrage entraînement BANDA AI v1...")
    history = model.fit(train_ds, epochs=EPOCHS, callbacks=callbacks)
    
    # Export TFLite quantizé (INT8 pour mobile bas de gamme)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.int8]
    tflite_model = converter.convert()
    
    Path(MODEL_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_OUTPUT, "wb") as f:
        f.write(tflite_model)
    
    print(f"✅ Modèle exporté: {MODEL_OUTPUT} ({len(tflite_model)//1024} KB)")
