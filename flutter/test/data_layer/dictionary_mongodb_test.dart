import 'package:flutter_test/flutter_test.dart';
import 'package:matica/data_layer/dictionary_mongodb.dart';

void main() {
  late DictionaryMongodbProvider dictionary;
  group('Tests with self-initialized DB', () {
    setUp(() {
      dictionary =
          DictionaryMongodbProvider(connectionString: "mongodb://localhost:27017/matica");
    });

    tearDown(() {
      dictionary.destroy();
    });

    test('MaticaMongoDb init', () async {
      await dictionary.init();
    });
  });

  group('Tests with already initialized DB', () {
    setUp(() async {
      dictionary =
          DictionaryMongodbProvider(connectionString: "mongodb://localhost:27017/matica");
      await dictionary.init();
    });

    tearDown(() {
      dictionary.destroy();
    });

    test('MaticaDictionary getEntriesByHeadwordBegin', () async {
      final results = await dictionary.getEntriesByHeadwordBegin('хок');
      expect(results.length, equals(8));
    });
  });
}
