import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:logger/logger.dart';
import 'package:mongo_dart/mongo_dart.dart';

import 'dictionary.dart';

class DictionaryMongodbProvider implements DictionaryProvider {
  final Logger _logger;
  late final Db _db;
  late final DbCollection _collection;

  DictionaryMongodbProvider(Logger logger) : _logger = logger;

  @override
  Future<void> init() async {
    String? connectionString;
    if (!kIsWeb) {
      connectionString = Platform.environment['MONGO_CONNECTION_STRING'];
    }
    if (connectionString == null) {
      try {
        await dotenv.load(fileName: "assets/.env");
        connectionString = dotenv.env['MONGO_CONNECTION_STRING']!;
        _logger.d("Loaded .env file");
      } on Object catch (e) {
        String errorMessage = "Error loading .env file: $e.";
        connectionString = "mongodb://localhost:27017/matica";
        errorMessage += " Using default connection string.";
        FlutterError.reportError(FlutterErrorDetails(
          exception: Exception(errorMessage),
          stack: StackTrace.current,
        ));
      }
    }
    _logger.i(
        'MongoDB Connection string: ${connectionString.replaceFirst(RegExp(r'(?<=://).+?(?=@)'), '***:***')}');
    _db = await Db.create(connectionString);
    await _db.open();
    _collection = _db.collection('entries');
  }

  @override
  Future<List<DictionaryEntry>> getEntriesByHeadwordBegin(
      String pattern) async {
    if (pattern.isEmpty) {
      return [];
    }
    final regexPattern = '^$pattern';
    final match = where.match('headword', regexPattern, caseInsensitive: true);
    /*
    i want to see the match for "и"
    final count = await _collection.count(match);
    if (count > 1000) {
      return [];
    }
     */
    final results = _collection
        .find(match.limit(10))
        .map((e) => DictionaryEntry(
            headword: e['headword'], definition: e['definition']))
        .toList();
    return results;
  }

  @override
  Future<void> destroy() async {
    await _db.close();
  }
}
