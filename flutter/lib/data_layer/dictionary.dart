import 'package:equatable/equatable.dart';

class DictionaryEntry extends Equatable {
  final String headword;
  final String definition;

  @override
  List<Object> get props => [headword, definition];

  const DictionaryEntry({required this.headword, required this.definition});
}

abstract class DictionaryProvider {
  Future<void> destroy();
  Future<void> init();
  Future<List<DictionaryEntry>> getEntriesByHeadwordBegin(String pattern);
}