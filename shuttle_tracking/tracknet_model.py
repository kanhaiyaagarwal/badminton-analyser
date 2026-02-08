"""
TrackNetV2 model definition for shuttlecock detection.

Architecture: VGG16-style encoder + U-Net decoder with skip connections.
Input: 3 consecutive frames concatenated -> [batch, 9, 288, 512]
Output: [batch, 3, 288, 512] sigmoid heatmaps (one per input frame)

Note: The pre-trained weights (track.pt) were converted from TensorFlow where
BatchNorm operates on the width dimension (channels-last format). To load these
weights correctly, the Conv block transposes NCHW -> NWHC before BN and back.
The BN size parameter corresponds to the spatial width at each stage, not channels.

Reference: https://github.com/ChgygLin/TrackNetV2-pytorch
"""

import torch
import torch.nn as nn


class Conv(nn.Module):
    """Conv2d + ReLU + BatchNorm block (TF-compatible weight loading).

    The BN operates on the width dimension to match the TF-converted checkpoint.
    Args:
        ic: Input channels.
        oc: Output channels.
        bc: BatchNorm features (= spatial width at this stage).
    """

    def __init__(self, ic, oc, bc, k=(3, 3), p="same", act=True):
        super().__init__()
        self.conv = nn.Conv2d(ic, oc, kernel_size=k, padding=p)
        self.bn = nn.BatchNorm2d(bc)
        self.act = nn.ReLU() if act else nn.Identity()

    def forward(self, x):
        x = self.act(self.conv(x))
        x = x.transpose(1, 3)  # NCHW -> NWHC
        x = self.bn(x)
        x = x.transpose(1, 3)  # NWHC -> NCHW
        return x


class TrackNet(nn.Module):
    """TrackNetV2: VGG16 encoder + U-Net decoder for shuttlecock tracking."""

    def __init__(self):
        super().__init__()

        # Encoder (VGG16-style)
        # BN sizes correspond to spatial width: 512 -> 256 -> 128 -> 64
        # Block 1: input width=512
        self.conv2d_1 = Conv(9, 64, 512)
        self.conv2d_2 = Conv(64, 64, 512)
        self.max_pooling_1 = nn.MaxPool2d((2, 2), stride=(2, 2))

        # Block 2: width=256
        self.conv2d_3 = Conv(64, 128, 256)
        self.conv2d_4 = Conv(128, 128, 256)
        self.max_pooling_2 = nn.MaxPool2d((2, 2), stride=(2, 2))

        # Block 3: width=128
        self.conv2d_5 = Conv(128, 256, 128)
        self.conv2d_6 = Conv(256, 256, 128)
        self.conv2d_7 = Conv(256, 256, 128)
        self.max_pooling_3 = nn.MaxPool2d((2, 2), stride=(2, 2))

        # Block 4 (bottleneck): width=64
        self.conv2d_8 = Conv(256, 512, 64)
        self.conv2d_9 = Conv(512, 512, 64)
        self.conv2d_10 = Conv(512, 512, 64)

        # Decoder with skip connections
        # Up block 1: width=128
        self.up_sampling_1 = nn.UpsamplingNearest2d(scale_factor=2)
        self.conv2d_11 = Conv(768, 256, 128)
        self.conv2d_12 = Conv(256, 256, 128)
        self.conv2d_13 = Conv(256, 256, 128)

        # Up block 2: width=256
        self.up_sampling_2 = nn.UpsamplingNearest2d(scale_factor=2)
        self.conv2d_14 = Conv(384, 128, 256)
        self.conv2d_15 = Conv(128, 128, 256)

        # Up block 3: width=512
        self.up_sampling_3 = nn.UpsamplingNearest2d(scale_factor=2)
        self.conv2d_16 = Conv(192, 64, 512)
        self.conv2d_17 = Conv(64, 64, 512)

        # Final 1x1 conv to 3 output channels (no BN)
        self.conv2d_18 = nn.Conv2d(64, 3, kernel_size=(1, 1), padding="same")
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # Encoder
        # Block 1
        x1 = self.conv2d_1(x)
        x1 = self.conv2d_2(x1)
        x = self.max_pooling_1(x1)

        # Block 2
        x2 = self.conv2d_3(x)
        x2 = self.conv2d_4(x2)
        x = self.max_pooling_2(x2)

        # Block 3
        x3 = self.conv2d_5(x)
        x3 = self.conv2d_6(x3)
        x3 = self.conv2d_7(x3)
        x = self.max_pooling_3(x3)

        # Block 4 (bottleneck)
        x = self.conv2d_8(x)
        x = self.conv2d_9(x)
        x = self.conv2d_10(x)

        # Decoder
        # Up block 1: concat with block 3 output (512+256=768)
        x = self.up_sampling_1(x)
        x = torch.cat([x, x3], dim=1)
        x = self.conv2d_11(x)
        x = self.conv2d_12(x)
        x = self.conv2d_13(x)

        # Up block 2: concat with block 2 output (256+128=384)
        x = self.up_sampling_2(x)
        x = torch.cat([x, x2], dim=1)
        x = self.conv2d_14(x)
        x = self.conv2d_15(x)

        # Up block 3: concat with block 1 output (128+64=192)
        x = self.up_sampling_3(x)
        x = torch.cat([x, x1], dim=1)
        x = self.conv2d_16(x)
        x = self.conv2d_17(x)

        # Output
        x = self.conv2d_18(x)
        x = self.sigmoid(x)

        return x
