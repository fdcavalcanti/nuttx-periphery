"""Example: read and write per-channel PWM settings."""
import argparse
import sys
import time

from nuttx_periphery.pwm import PWM


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pwm",
        nargs="?",
        default="/dev/pwm0",
        help="PWM device path (default: /dev/pwm0)",
    )
    parser.add_argument(
        "-c",
        "--channels",
        type=int,
        default=1,
        help="Number of channels (default: 1)",
    )
    return parser.parse_args()


def main(args) -> int:
    pwm = PWM(args.pwm, channel_count=args.channels)
    print(pwm.list_channels())

    pwm.frequency = 200
    pwm.channel[0].duty = 45
    pwm.apply()

    print(f"PWM Frequency: {pwm.frequency}")
    print(f"PWM Channel 0 Duty: {pwm.channel[0].duty}")

    print("PWM starts for 5 seconds")
    pwm.start()
    time.sleep(5)
    pwm.stop()
    print("PWM stopped")

    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args))
