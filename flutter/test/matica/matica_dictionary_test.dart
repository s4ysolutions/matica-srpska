import 'package:flutter_test/flutter_test.dart';
import 'package:matica/services/matica.dart';

void main() {
  test('MaticaDictionary init', () async {
    final dictionary = MaticaDictionary();
    await dictionary.init();
  });

  test('MaticaDictionary getEntriesByHeadwordPattern', () async {
    final dictionary = MaticaDictionary();
    final results = await dictionary.getEntriesByHeadwordPattern('pattern');
    expect(results.length, greaterThan(0));
  });
}