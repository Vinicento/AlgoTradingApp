#main activator file
from sklearn.ensemble import BaggingClassifier
import app
import sys



if __name__ == "__main__":
    application = app.Application()
    sys.exit(application.app.exec_())
