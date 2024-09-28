import 'package:flutter_test/flutter_test.dart';
import 'package:matica/data_layer/dictionary_random.dart';

void main() {
  test('MaticaDictionary init', () async {
    final dictionary = DictionaryRandomProvider();
    await dictionary.init();
  });

  test('MaticaDictionary getEntriesByHeadwordPattern', () async {
    final dictionary = DictionaryRandomProvider();
    final results = await dictionary.getEntriesByHeadwordBegin('pattern');
    // sporadically fails - i can not find the reason
    expect(results.length, greaterThan(0));
  });
}