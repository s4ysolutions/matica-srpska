import 'package:mongo_dart/mongo_dart.dart';

import 'dictionary.dart';

class DictionaryMongodbProvider implements DictionaryProvider {
  final String connectionString;
  late final Db _db;
  late final DbCollection _collection;

  DictionaryMongodbProvider({this.connectionString = 'mongodb://localhost:27017/matica'});

  @override
  Future<void> init() async {
    _db = await Db.create(connectionString);
    await _db.open();
    _collection = _db.collection('entries');
  }

  @override
  Future<List<DictionaryEntry>> getEntriesByHeadwordBegin(String pattern) async {
    final regexPattern = '^$pattern';
    final results = _collection
        .find(where
            .match('headword', regexPattern, caseInsensitive: true)
            .limit(100))
        .map((e) =>
            DictionaryEntry(headword: e['headword'], definition: e['definition']))
        .toList();
    return results;
  }

  @override
  Future<void> destroy() async {
    await _db.close();
  }
}
