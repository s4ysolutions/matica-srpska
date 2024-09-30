import 'dart:math';

import 'package:english_words/english_words.dart';
import 'package:lorem_ipsum/lorem_ipsum.dart';

import 'dictionary.dart';

class DictionaryRandomProvider implements DictionaryProvider {

  const DictionaryRandomProvider();

  @override
  Future<void> init() async {
    return Future.delayed(const Duration(seconds: 1));
  }

  @override
  Future<List<DictionaryEntry>> getEntriesByHeadwordBegin(
      String pattern) async {
    final random = Random();
    final nRandom = 3 + random.nextInt(12);
    final results = <DictionaryEntry>[];
    while (results.isEmpty) {
      for (var i = 3; i < nRandom; i++) {
        await Future.delayed(const Duration(milliseconds: 50));
        String definition = loremIpsum(words: 5 + random.nextInt(20));
        results.add(DictionaryEntry(
            headword: WordPair.random().asString, definition: definition));
      }
      return results;
    }
    throw Exception("Must not reach here");
  }

  @override
  Future<void> destroy() {
    return Future.delayed(const Duration(milliseconds: 100));
  }
}
