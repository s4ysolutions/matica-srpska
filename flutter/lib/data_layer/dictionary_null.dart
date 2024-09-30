import 'package:matica/data_layer/dictionary.dart';

class DictionaryNullProvider extends DictionaryProvider {
  @override
  Future<void> init() async {
    return;
  }

  @override
  Future<List<DictionaryEntry>> getEntriesByHeadwordBegin(
      String pattern) async {
    return [];
  }

  @override
  Future<void> destroy() async {
    return;
  }
}