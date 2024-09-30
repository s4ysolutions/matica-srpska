import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:logger/logger.dart';
import 'package:matica/data_layer/dictionalry_rtdb.dart';
import 'package:matica/data_layer/dictionary_mongodb.dart';
import 'package:matica/services/matica.dart';
import 'package:provider/provider.dart';

import 'data_layer/dictionary.dart';
import 'flutter/ui/homePage/main.dart';

void main() {
  final logger = Logger();
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
  };

  final DictionaryProvider dictionaryProvider =
      DictionaryRTDBProvider("entries", logger: logger);
  DictionaryMongodbProvider(logger);

  runZonedGuarded(() {
    runApp(MyApp(logger: logger, dictionaryProvider: dictionaryProvider));
  }, (e, s) {
    FlutterError.reportError(FlutterErrorDetails(exception: e, stack: s));
  });
}

class MyApp extends StatelessWidget {
  final Logger _logger;
  final DictionaryProvider _dictionaryProvider;

  const MyApp(
      {super.key,
      required Logger logger,
      required DictionaryProvider dictionaryProvider})
      : _logger = logger,
        _dictionaryProvider = dictionaryProvider;

  @override
  Widget build(BuildContext context) {
    _logger.d("MyApp build");
    return MultiProvider(
        providers: [
          Provider<MaticaService>(
              create: (_) => MaticaService(_dictionaryProvider, _logger)),
          Provider<Logger>(create: (_) => _logger),
          StreamProvider<MaticaSearchResults>(
              create: (_) =>
                  Provider.of<MaticaService>(context).searchResultsStream,
              initialData: MaticaSearchResults.empty),
          StreamProvider<MaticaSearchState>(
              create: (_) =>
                  Provider.of<MaticaService>(context).searchStateStream,
              initialData: MaticaSearchState.uninitialized),
        ],
        child: MaterialApp(
            title: 'Flutter Demo',
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            theme: ThemeData(
              colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
              useMaterial3: true,
            ),
            home: InitWrapper()));
  }
}

class InitWrapper extends StatefulWidget {
  const InitWrapper({super.key});

  @override
  State<StatefulWidget> createState() => _InitWrapperState();
}

class _InitWrapperState extends State<InitWrapper> {
  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      Provider.of<Logger>(context, listen: false).d("InitWrapper initState");
      await Provider.of<MaticaService>(context, listen: false)
          .init();
    });
  }

  @override
  Widget build(BuildContext context) {
    return HomePage(title: AppLocalizations.of(context)!.homePageTitle);
  }
}
