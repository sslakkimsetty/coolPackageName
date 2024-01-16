import tensorflow as tf
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers
from tensorflow.keras.layers import Dense, Dropout, Conv2D, Reshape, Flatten, MaxPooling2D
from ..stn_bspline import SpatialTransformerBspline


class Linear(layers.Layer):
    """
    Custom linear layer for neural networks.

    This layer performs a linear transformation on the input data using weights (w) and biases (b).
    The transformation is defined as: output = inputs * w + b.

    Parameters:
    - units (int): Number of output units/neurons in the layer.
    - input_dim (int): Dimensionality of the input data.
    - is_transformer_regressor (bool): If True, initializes weights with zeros and uses a trainable bias based on a
                                       transformer regressor approach.
                                       If False, initializes weights with random values and uses a trainable bias
                                       initialized with zeros.

    Attributes:
    - w (tf.Variable): Weight matrix for the linear transformation.
    - b (tf.Variable): Bias vector for the linear transformation.

    Methods:
    - call(inputs): Performs the linear transformation on the input data.

    Example usage:
    ```python
    linear_layer = Linear(units=64, input_dim=128, is_transformer_regressor=False)
    output_data = linear_layer(input_data)
    ```

    Note: This class is designed to be used as a layer within a TensorFlow/Keras model.
    """
    def __init__(self, units=32, input_dim=32, is_transformer_regressor=False):
        super(Linear, self).__init__()

        if is_transformer_regressor:
            w_init = tf.zeros_initializer()  # initialize weights with zeros
            theta = np.zeros(shape=(units,))  # initialize biases with zeros
            theta = tf.cast(theta, "float32")
            self.b = tf.Variable(initial_value=theta, trainable=True)
        else:
            w_init = tf.random_normal_initializer()  # initialize weights with random values
            b_init = tf.zeros_initializer()  # initialize biases as zeros
            self.b = tf.Variable(initial_value=b_init(shape=(units,), dtype="float32"), trainable=True)

        self.w = tf.Variable(initial_value=w_init(shape=(input_dim, units), dtype="float32"), trainable=True)

    def call(self, inputs):
        """
        Perform a linear transformation on the input data.

        Given input data `inputs`, apply a linear transformation using the weights (w) and biases (b) of the layer.
        The transformation is defined as: output = inputs * w + b.

        Parameters:
        - inputs (tf.Tensor): Input data to be transformed.

        Returns:
        - tf.Tensor: Output of the linear transformation.
        """
        return tf.matmul(inputs, self.w) + self.b


class LocNet(tf.keras.layers.Layer):
    """
    Localization Network (LocNet) layer for spatial feature extraction.

    This layer consists of two convolutional blocks followed by max-pooling operations.

    Parameters:
    None

    Attributes:
    - conv1 (tf.keras.layers.Conv2D):
            First convolutional layer with 8 filters and a kernel size of 7x7, using ReLU activation.
    - maxpool1 (tf.keras.layers.MaxPooling2D):
            First max-pooling layer with a pool size of 2x2 and strides of 2.
    - conv2 (tf.keras.layers.Conv2D):
            Second convolutional layer with 10 filters and a kernel size of 5x5, using ReLU activation.
    - maxpool2 (tf.keras.layers.MaxPooling2D):
            Second max-pooling layer with a pool size of 2x2 and strides of 2.

    Methods:
    - call(inputs): Applies the LocNet layer on the input data, extracting spatial features.

    Example usage:
    ```python
    locnet_layer = LocNet()
    input_data = tf.random.normal(shape=(batch_size, height, width, channels))
    output_features = locnet_layer(input_data)
    ```

    Note: This class is designed to be used as a part of a neural network, particularly for spatial feature extraction
    in tasks such as image localization or object detection.
    """
    def __init__(self):
        super(LocNet, self).__init__()

        self.conv1 = Conv2D(filters=8, kernel_size=7, activation="relu")
        self.maxpool1 = MaxPooling2D(pool_size=(2,2), strides=2)
        self.conv2 = Conv2D(filters=10, kernel_size=5, activation="relu")
        self.maxpool2 = MaxPooling2D(pool_size=(2,2), strides=2)

    def call(self, inputs):
        """
        Apply the LocNet layer on the input data to extract spatial features.

        This method takes an input tensor `inputs` and applies the LocNet layer.

        Parameters:
        - inputs (tf.Tensor): Input data tensor with shape (batch_size, height, width, channels).

        Returns:
        - tf.Tensor: Output tensor representing the spatial features extracted by the LocNet layer.
        """
        x = self.conv1(inputs)
        x = self.maxpool1(x)
        x = self.conv2(x)
        x = self.maxpool2(x)
        return x


class TransformationRegressor(tf.keras.layers.Layer):
    """
    Transformation Regressor layer for predicting transformation parameters.

    This layer is designed to predict transformation parameters, such as rotation or translation, from input data.
    It consists of two linear layers with optional activation functions.

    Parameters:
    - theta_units (int): Number of units in the intermediate layer used for predicting transformation parameters.
    - input_dim (int): Dimensionality of the input data. If None, it will be inferred during the first forward pass.

    Attributes:
    - linear1 (Linear): First linear layer with units=theta_units*5, responsible for extracting features from the input.
    - linear2 (Linear): Second linear layer with units=theta_units, specifically designed for predicting transformation
                        parameters. If is_transformer_regressor is True, it uses a custom initialization for
                        transformer regression.

    Methods:
    - call(inputs): Applies the Transformation Regressor layer on the input data to predict transformation parameters.

    Example usage:
    ```python
    regressor_layer = TransformationRegressor(theta_units=6, input_dim=10)
    input_data = tf.random.normal(shape=(batch_size, input_dim))
    transformation_params = regressor_layer(input_data)
    ```

    Note: This class is intended to be used as a part of a neural network, especially for tasks involving predicting
    transformation parameters from input data.
    """
    def __init__(self, theta_units=6, input_dim=None):
        super(TransformationRegressor, self).__init__()

        self.linear1 = Linear(units=theta_units*5, input_dim=input_dim)
        self.linear2 = Linear(units=theta_units, input_dim=theta_units*5, is_transformer_regressor=True)

    def call(self, inputs):
        """
        Apply the Transformation Regressor layer on the input data to predict transformation parameters.

        This method takes an input tensor `inputs` and applies the Transformation Regressor layer,
        consisting of two linear layers with tanh activation functions.
        The purpose is to predict transformation parameters, such as rotation or translation, from the input data.

        Parameters:
        - inputs (tf.Tensor): Input data tensor with shape (batch_size, input_dim).

        Returns:
        - tf.Tensor: Output tensor representing the predicted transformation parameters.
        """
        x = self.linear1(inputs)
        x = tf.nn.tanh(x)
        x = self.linear2(x)
        x = tf.nn.tanh(x)
        return x


class DLIR(tf.keras.models.Model):
    """
    Deep Learning Image Regressor (DLIR) model for spatial transformation.

    This model combines a localization network (LocNet), a spatial transformer module (SpatialTransformerBspline),
    and a transformation regressor to enable spatial transformations on input images.

    Parameters:
    - drate (float): Dropout rate for regularization.
    - grid_res (tuple): Resolution of the transformation grid (sx, sy).
    - img_res (tuple): Resolution of the input image (H, W).
    - input_dim (int): Dimensionality of the input data.

    Attributes:
    - grid_res (tuple): Resolution of the transformation grid (sx, sy).
    - img_res (tuple): Resolution of the input image (H, W).
    - drate (float): Dropout rate for regularization.
    - B (int): Spline basis degree.
    - loc_net (LocNet): Localization network for spatial feature extraction.
    - flatten (Flatten): Flatten layer for transforming spatial features into a 1D vector.
    - transformer (SpatialTransformerBspline): Spatial transformer module for image transformation.
    - transformer_regressor (TransformationRegressor): Regressor for predicting transformation parameters.

    Methods:
    - call(inputs): Applies the DLIR model on the input data to perform spatial transformations.
    - transform(inputs): Applies the DLIR model to perform spatial transformations without dropout.

    Example usage:
    ```python
    dlir_model = DLIR(drate=0.2, grid_res=(5, 5), img_res=(256, 256), input_dim=512)
    input_data = tf.random.normal(shape=(batch_size, 256, 256, 3))
    transformed_output = dlir_model.call(input_data)
    ```

    Note: This class is designed to be used as a Keras model for tasks involving spatial transformations on images.
    """
    def __init__(self, drate=0.2, grid_res=None, img_res=None,
        input_dim=None):
        super(DLIR, self).__init__()
        self.grid_res = grid_res
        self.img_res = img_res
        self.drate = drate
        self.B = 1

        self.loc_net = LocNet()
        self.flatten = Flatten()
        self.transformer = SpatialTransformerBspline(img_res=self.img_res,
                                                     grid_res=self.grid_res,
                                                     out_dims=None,
                                                     B=self.B)

        sx, sy = self.grid_res
        H, W = self.img_res
        gx, gy = tf.math.ceil(W/sx), tf.math.ceil(H/sy)
        nx, ny = tf.cast(gx+3, tf.int32), tf.cast(gy+3, tf.int32)

        self.transformer_regressor = TransformationRegressor(theta_units=2*ny*nx, input_dim=input_dim)


    def call(self, inputs):
        """
        Apply the DLIR model on the input data to perform spatial transformations.

        Parameters:
        - inputs (tf.Tensor): Input data tensor with shape (batch_size, H, W, channels).

        Returns:
        - tf.Tensor: Transformed output tensor.
        """
        xs = self.loc_net(inputs)
        xs = self.flatten(xs)
        xs = Dropout(rate=self.drate)(xs)
        theta = self.transformer_regressor(xs)
        xt = self.transformer(inputs, theta, self.B)
        return xt


    def transform(self, inputs):
        """
        Apply the DLIR model to perform spatial transformations without dropout.

        Parameters:
        - inputs (tf.Tensor): Input data tensor with shape (batch_size, H, W, channels).

        Returns:
        - tf.Tensor: Transformed output tensor.
        """
        # inputs = inputs.astype("float32")
        inputs = tf.cast(inputs, "float32")
        xs = self.loc_net(inputs)
        xs = self.flatten(xs)
        theta = self.transformer_regressor(xs)
        xt = self.transformer(inputs, theta, self.B)
        return xt


class BSplineRegistration(tf.keras.models.Model):
    """
    B-Spline Registration model for non-linear image registration.

    This model combines a localization network (LocNet), a transformation regressor, and a B-spline-based spatial
    transformer module to perform non-linear image registration.

    Parameters:
    - img_res (tuple): Resolution of the input images (H, W).
    - factor (int): Upsampling factor for the grid resolution in the spatial transformer module.

    Attributes:
    - B (int): Spline basis degree.
    - img_res (tuple): Resolution of the input images (H, W).
    - loc_net (LocNet): Localization network for spatial feature extraction.
    - grid_res (list): Resolution of the B-spline grid used in the spatial transformer module.
    - transformer_regressor (TransformationRegressor): Regressor for predicting B-spline transformation parameters.
    - transformer (SpatialTransformerBspline): Spatial transformer module using B-spline interpolation for image
                                               registration.

    Methods:
    - call(moving): Applies the B-Spline Registration model on the moving image to perform non-linear image
                    registration.

    Example usage:
    ```python
    bspline_model = BSplineRegistration(img_res=(256, 256), factor=2)
    moving_image = tf.random.normal(shape=(batch_size, 256, 256, 1))
    registered_image, transformation_params = bspline_model.call(moving_image)
    ```

    Note: This class is designed to be used as a Keras model for non-linear image registration using B-spline interpolation.
    """
    def __init__(self, img_res, factor=1):
        super(BSplineRegistration, self).__init__()
        self.B = 1
        self.img_res = img_res
        self.loc_net = LocNet()

        _test_arr = np.ones((1, img_res[0], img_res[1], 1)).astype(np.float32)
        _test_arr = self.loc_net(_test_arr)
        self.grid_res = _test_arr.numpy().squeeze().shape
        self.grid_res = [self.grid_res[0], self.grid_res[1]]
        print("Grid res:", self.grid_res)

        self.transformer_regressor = TransformationRegressor(theta_units=self.grid_res[0] * self.grid_res[1] * 2,
                                                             input_dim=factor)
        self.grid_res = [self.grid_res[0] * np.sqrt(factor).astype(np.int32),
                         self.grid_res[1] * np.sqrt(factor).astype(np.int32)]
        self.transformer = SpatialTransformerBspline(img_res=img_res,
                                                     grid_res=self.grid_res,
                                                     out_dims=img_res,
                                                     B=self.B)

    def call(self, moving):
        """
        Apply the B-Spline Registration model on the moving image for non-linear image registration.

        Parameters:
        - moving (tf.Tensor): Tensor representing the moving image with shape (batch_size, H, W, channels).

        Returns:
        - tf.Tensor: Registered image tensor.
        - tf.Tensor: B-spline transformation parameters.
        """
        xs = moving
        xs = self.loc_net(xs)
        xs = tf.transpose(xs, [0, 3, 1, 2])
        theta = self.transformer_regressor(xs)
        theta = tf.reshape(theta, (self.B, 2, self.grid_res[0], self.grid_res[1]))
        xt = self.transformer(moving, theta, self.B)
        return xt, theta


