# exdbproject

## Setting up the development environment on Linux
1. Clone into the Git repository

  ```shell
  git clone https://github.com/mostateresnet/exdbproject.git
  ```
2. Switch to the newly created `exdbproject` directory

  ```shell
  cd exdbproject
  ```
3. Create a new virtual environment for EXDB

  ```shell
  mkvirtualenv --python=$(which python3.5) exdbproject
  ```
4. Install the required Python packages

  ```shell
  pip install -U pip -r requirements/development.txt
  ```
5. Install the required Node.js packages (this will take several minutes to compile)

  ```shell
  nodeenv -p --requirements=requirements/node_packages.txt --jobs=4
  ```
6. Re-activate the Python virtual environment to ensure all the environment variables are reset to their proper values

  ```shell
  workon exdbproject
  ```
7. Test that everything worked

  ```shell
  ./manage.py verify
  ```

## Testing Dependencies
We use Selenium for UI testing.
Selenium has the requirement that the drivers for the respective clients are present in the system path.
To run the tests you must have the drivers for at least the browsers you would like to test, as well as the actual browser installed.
Many if not all of the drivers are linked at http://www.seleniumhq.org/download/.

## Testing
To test using your browser of choice pass the -b option to manage.py test (phantomjs is the default):
```shell
python manage.py test -b chrome
``` 

If you would like to test using an android device you will need to setup the Remote webdriver for android then you can specify the broadcast address for the test server:
```shell
python manage.py test -b remote --liveserver=0.0.0.0:8081
```
The test runner will automatically try to acertain and test using the hostname of the machine running the tests if the ip is 0.0.0.0
