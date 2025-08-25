from pynput.mouse import Button, Controller
import time

def main():
    mouse = Controller()

    while True:
        print('The current pointer position is {0}'.format(
            mouse.position))
        time.sleep(1)


if __name__ == '__main__':
    main()