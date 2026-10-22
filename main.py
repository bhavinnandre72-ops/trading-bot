import multiprocessing
import os


def run_crude():
  os.system("python crude_bot.py")


def run_natgas():
  os.system("python natgas_bot.py")


if __name__ == "__main__":
  p1 = multiprocessing.Process(target=run_crude)
  p2 = multiprocessing.Process(target=run_natgas)

  p1.start()
  p2.start()

  p1.join()
  p2.join()
  
