#!/usr/bin/env python3
"""Publish paced JPEG topics expected by the Edgematic Flora demo layout."""

from __future__ import annotations

import argparse
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image


DEFAULT_TOPICS = ("/image_raw", "/detections_overlay")


def jpeg_quality(value: str) -> int:
    quality = int(value)
    if not 1 <= quality <= 100:
        raise argparse.ArgumentTypeError("must be between 1 and 100")
    return quality


class JpegRepublisher(Node):
    def __init__(self, topics: tuple[str, ...], quality: int, max_fps: float) -> None:
        super().__init__("edgematic_jpeg_republisher")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
        )
        self._quality = quality
        self._minimum_period = 1.0 / max_fps
        self._last_publish = {topic: 0.0 for topic in topics}
        self._publishers = {
            topic: self.create_publisher(CompressedImage, f"{topic}/compressed", qos)
            for topic in topics
        }
        self._subscriptions = [
            self.create_subscription(
                Image,
                topic,
                lambda message, source=topic: self._publish(source, message),
                qos,
            )
            for topic in topics
        ]
        self.get_logger().info(
            f"publishing JPEG quality {quality} at up to {max_fps:g} fps: "
            + ", ".join(f"{topic}/compressed" for topic in topics)
        )

    def _publish(self, source: str, message: Image) -> None:
        now = time.monotonic()
        if now - self._last_publish[source] < self._minimum_period:
            return
        if message.encoding not in ("bgr8", "rgb8"):
            self.get_logger().error(
                f"unsupported {source} encoding: {message.encoding}",
                throttle_duration_sec=5.0,
            )
            return

        row_bytes = message.width * 3
        if message.step < row_bytes:
            self.get_logger().error(
                f"invalid {source} step {message.step} for width {message.width}",
                throttle_duration_sec=5.0,
            )
            return
        rows = np.frombuffer(message.data, dtype=np.uint8).reshape(
            message.height, message.step
        )
        frame = rows[:, :row_bytes].reshape(message.height, message.width, 3)
        if message.encoding == "rgb8":
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        encoded, jpeg = cv2.imencode(
            ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self._quality]
        )
        if not encoded:
            self.get_logger().error(
                f"JPEG encoding failed for {source}", throttle_duration_sec=5.0
            )
            return

        output = CompressedImage()
        output.header = message.header
        output.format = "jpeg"
        output.data = jpeg.tobytes()
        self._publishers[source].publish(output)
        self._last_publish[source] = now


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", action="append", dest="topics")
    parser.add_argument("--quality", type=jpeg_quality, default=70, metavar="1..100")
    parser.add_argument("--max-fps", type=float, default=10.0)
    args, ros_args = parser.parse_known_args()
    if args.max_fps <= 0:
        parser.error("--max-fps must be greater than zero")
    return args, ros_args


def main() -> None:
    args, ros_args = parse_args()
    topics = tuple(args.topics or DEFAULT_TOPICS)
    rclpy.init(args=ros_args)
    node = JpegRepublisher(topics, args.quality, args.max_fps)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
