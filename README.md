# Matica Serpska

**Online and mobile Serbian Language Dictionaries**

## Motivation

Matica Srpska (Матица Српска) is a comprehensive dictionary of Serbian words explained in Serbian, which is
regarded as the most authoritative source of truth for other dictionaries.

This is the reason to have it in addition to dictionaries of other languages.

## Status

While the overall functionality is in place, the dictionary contains lot of errors due to OCR and manual
transcription. The process of cleaning up the dictionary is ongoing - please don't report about the noticed errors.

The online version of the dictionary is available at [Matica Srpska](https://matica-srpska-sy4.web.app).
Mobile and desktop versions are not yet published anywhere, but they are proven to be working and can be built from
the source code.

# Dictionary origin

The dictionary is based on the 2011 edition of the Matica Srpska dictionary, which is
in [public domain](https://archive.org/details/recnik-srpskoga-jezika-2011) by parsing the PDF created by OSR
the paper book.

The conversion script is available in
the [convertor.py](https://github.com/s4ysolutions/matica-srpska/blob/main/convertor/convertor.py)
script.

## Build

The build process is more or less straightforward according to the Flutter documentation. But some additional steps
were needed to be done:

Firebase realtime database (if used) requires the specific setup https://firebase.google.com/docs/flutter/setup?platform=ios
MongoDB (if used) requires `assets/.env` file with the `MONGO_CONNECTION_STRING` variable.

Building for iOS causes the build error which is fixed by the following solution: https://stackoverflow.com/questions/56500709/how-to-connect-to-a-local-mongodb-instance-from-wasm-module

## Features

The application is developed in Flutter and Dart, and it is available for Mac, Windows(unchecked), Android, iOS, and Web.

Currently, there are 2 backends supported: MongoDB(is not available for Web) and Firebase.

The architecture follows the Clean Architecture principles:

 - [data layer](https://github.com/s4ysolutions/matica-srpska/tree/main/flutter/lib/data_layer) contains the
implementations of `DictionaryProvider` interface, which is used to implement search operations using concrete
backend with Future-based API.
 - [domain layer](https://github.com/s4ysolutions/matica-srpska/blob/main/flutter/lib/services/matica.dart) contains
the `MaticaService` class, which leverages the `DictionaryProvider` interface to provide search functionality using
the Streams API. The choice of Streams for delivering search results serves as a demonstration of Flutter’s ability to
handle reactive programming.
 - [presentation layer](https://github.com/s4ysolutions/matica-srpska/blob/37916868bdc829e6adaada5cc8ab3cd311e80752/flutter/lib/main.dart#L45)
 with Provider and StreamProvider widgets to provide the search functionality to the UI layer.
 - [ui layer](https://github.com/s4ysolutions/matica-srpska/blob/main/flutter/lib/flutter/ui/homePage/main.dart) uses
Provider's Consumer widget of the presentation layer to [listen for search results](https://github.com/s4ysolutions/matica-srpska/blob/37916868bdc829e6adaada5cc8ab3cd311e80752/flutter/lib/flutter/ui/homePage/search_results.dart#L38)
 stream and breaks the CA a bit by [using the `MaticaService` directly](https://github.com/s4ysolutions/matica-srpska/blob/37916868bdc829e6adaada5cc8ab3cd311e80752/flutter/lib/flutter/ui/homePage/search_field.dart#L22) to perform the search operation.

## Known issues

 - Error handling is not consistent across the application mainly due to Flutter limitations in handling errors in the
non-waited Futures. Sometimes the error just passed to the [default error handler](https://github.com/s4ysolutions/matica-srpska/blob/37916868bdc829e6adaada5cc8ab3cd311e80752/flutter/lib/main.dart#L16),
 and sometimes they are catched and forced to be [routed to that handler](
   https://github.com/s4ysolutions/matica-srpska/blob/37916868bdc829e6adaada5cc8ab3cd311e80752/flutter/lib/flutter/ui/homePage/search_field.dart#L24).
