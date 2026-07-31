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
3. Install required Python version and dependencies in the virtual environment

  ```shell
  uv sync
  ```
  OR if you want to install production server dependencies:
  ```shell
  uv sync --group prod
```
4. Install the required Node.js packages using:

  ```shell
  uv run nodeenv -p --prebuilt --requirements=requirements/node_packages.txt
  ```
  OR compile Node.js from source with:
  ```shell
  uv run nodeenv -p --source --requirements=requirements/node_packages.txt --jobs=4
  ```
5. Test that everything worked

  ```shell
  uv run python manage.py verify
  ```
6. Start the dev server

  ```shell
  uv run python manage.py runserver 0.0.0.0:8000
  ```

## Testing Dependencies
We use Selenium for UI testing.
Selenium has the requirement that the drivers for the respective clients are present in the system path.
To run the tests you must have the drivers for at least the browsers you would like to test, as well as the actual browser installed.
Many if not all of the drivers are linked at http://www.seleniumhq.org/download/.

## Testing
To test using your browser of choice pass the -b option to manage.py test (phantomjs is the default):
```shell
uv run python manage.py test -b chrome
``` 

If you would like to test using an android device you will need to setup the Remote webdriver for android then you can specify the broadcast address for the test server:
```shell
uv run python manage.py test -b remote --liveserver=0.0.0.0:8081
```
The test runner will automatically try to acertain and test using the hostname of the machine running the tests if the ip is 0.0.0.0
