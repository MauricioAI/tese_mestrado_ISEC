"""
Reference: 
    https://keras.io/examples/vision/image_classification_with_vision_transformer/
"""

import tensorflow as tf
from tensorflow.keras import layers


def mlp(x, hidden_units, dropout_rate):
    for units in hidden_units:
        x = layers.Dense(units, activation = tf.nn.gelu)(x)
        x = layers.Dropout(dropout_rate)(x)
    return x


class Patches(layers.Layer):
    def __init__(self, patch_size):
        super(Patches, self).__init__()
        self.patch_size = patch_size

    def call(self, images):
        batch_size = tf.shape(images)[0]
        patches = tf.image.extract_patches(
            images = images,
            sizes = [1, self.patch_size, self.patch_size, 1],
            strides = [1, self.patch_size, self.patch_size, 1],
            rates = [1, 1, 1, 1],
            padding = 'VALID')
        patch_dims = patches.shape[-1]
        patches = tf.reshape(patches, [batch_size, -1, patch_dims])
        return patches


class PatchEncoder(layers.Layer):
    def __init__(self, num_patches, projection_dim):
        super(PatchEncoder, self).__init__()
        self.num_patches = num_patches
        self.projection = layers.Dense(units = projection_dim)
        self.position_embedding = layers.Embedding(input_dim = num_patches, output_dim = projection_dim)

    def call(self, patch):
        positions = tf.range(start = 0, limit = self.num_patches, delta = 1)
        encoded = self.projection(patch) + self.position_embedding(positions)
        return encoded
    
class StudentViT:
    def __init__(self, aPatchSize):
        self.patch_size = aPatchSize
        self.projection_dim = 32
        self.num_heads = 3
        self.transformer_layers = 4
        self.mlp_head_units = [1024, 512]
    
    def call(self,inputs):
        num_patches = (224 // self.patch_size) ** 2
        transformer_units = [self.projection_dim * 2, self.projection_dim]

        # Create patches.
        patches = Patches(self.patch_size)(inputs)
        
        # Encode patches.
        encoded_patches = PatchEncoder(num_patches, self.projection_dim)(patches)

        # Create multiple layers of the Transformer block.
        for _ in range(self.transformer_layers):
            
            # Layer normalization 1.
            x1 = layers.LayerNormalization(epsilon = 1e-6)(encoded_patches)
            
            # Create a multi-head attention layer.
            attention_output = layers.MultiHeadAttention(num_heads = self.num_heads, key_dim = self.projection_dim, dropout = 0.1)(x1, x1)
            
            # Skip connection 1.
            x2 = layers.Add()([attention_output, encoded_patches])
            
            # Layer normalization 2.
            x3 = layers.LayerNormalization(epsilon = 1e-6)(x2)
            
            # MLP.
            x3 = mlp(x3, hidden_units = transformer_units, dropout_rate = 0.1)
            
            # Skip connection 2.
            encoded_patches = layers.Add()([x3, x2])

        # Create a [batch_size, projection_dim] tensor.
        representation = layers.LayerNormalization(epsilon = 1e-6)(encoded_patches)
        representation = layers.Flatten()(representation)
        representation = layers.Dropout(0.5)(representation)
        
        # Add MLP.
        features = mlp(representation, hidden_units = self.mlp_head_units, dropout_rate = 0.5)
        
        # Classify outputs.
        outputs = layers.Dense(2)(features)
        
        return outputs