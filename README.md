# exdbproject

## Testing Dependencies
We use Selenium for UI testing.
Selenium has the requirement that the drivers for the respective clients are present in the system path.
To run the tests you must have the drivers for at least the browsers you would like to test, as well as the actual browser installed.
Many if not all of the drivers are linked at http://www.seleniumhq.org/download/.

## Testing
To test using your browser of choice pass the -b option to manage.py test (phantomjs is the default):
```
python manage.py test -b chrome
``` 

If you would like to test using an android device you will need to setup the Remote webdriver for android then you can specify the broadcast address for the test server:
```
python manage.py test -b remote --liveserver=0.0.0.0:8081
```
The test runner will automatically try to acertain and test using the hostname of the machine running the tests if the ip is 0.0.0.0
