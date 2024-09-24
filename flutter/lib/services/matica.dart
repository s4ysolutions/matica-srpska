import 'dart:math';

import 'package:english_words/english_words.dart';
import 'package:lorem_ipsum/lorem_ipsum.dart';

class MaticaEntry {
  final String headword;
  final String description;

  const MaticaEntry({required this.headword, required this.description});
}

class MaticaDictionary{
  Future<void> init() async{
    return Future.delayed(const Duration(seconds: 1));
  }

  Future<List<MaticaEntry>> getEntriesByHeadwordPattern(String pattern) async{
    final random = Random();
    int nResults = random.nextInt(11);
    final results = <MaticaEntry>[];
    for (var i = 3; i < nResults; i++) {
      await Future.delayed(const Duration(milliseconds: 100));
      String description = loremIpsum(words: 5+random.nextInt(20));
      results.add(MaticaEntry(
          headword: WordPair.random().asString,
          description: description));
    }
    return results;
  }
}