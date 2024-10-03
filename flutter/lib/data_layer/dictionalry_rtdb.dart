import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_database/firebase_database.dart';
import 'package:logger/logger.dart';

import '../firebase_options.dart';
import 'dictionary.dart';

class DictionaryRTDBProvider implements DictionaryProvider {
  late final DatabaseReference _ref;
  final Logger _logger;

  DictionaryRTDBProvider(String path, {required Logger logger})
      : _logger = logger;

  @override
  Future<void> init() async {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
    _ref = FirebaseDatabase.instance.ref("entries");
  }

  static String _normalize(String s) {
    return s.replaceAll(' ', '').toLowerCase();
  }

  @override
  Future<List<DictionaryEntry>> getEntriesByHeadwordBegin(
      String pattern) async {
    if (pattern.isEmpty) {
      return [];
    }
    String lookupPattern = _normalize(pattern);
    final event = await _ref
        .orderByChild("lookup")
        .startAt(lookupPattern)
        .limitToFirst(25)
        .once();
    final snapshot = event.snapshot;
    final results = <DictionaryEntry>[];
    if (snapshot.value != null) {
      var value = snapshot.value;
      List<Map> entries = [];
      if (value is List) {
        entries = List<Map>.from(value);
      } else if (value is Map) {
        entries = List<Map>.from(value.values);
      } else {
        return [];
      }
      entries.forEach((value) {
        String headword = value["headword"] as String;
        String definition = value["definition"] as String;
        String lookup = _normalize(headword + definition);
        if (lookup.startsWith(lookupPattern)) {
          results
              .add(DictionaryEntry(headword: headword, definition: definition));
        }
      });
    }

    results.sort((a, b) {
      String aKey = (a.headword + a.definition).replaceAll(' ', '');
      String bKey = (b.headword + b.definition).replaceAll(' ', '');
      return aKey.compareTo(bKey);
    });

    return results;
  }

  @override
  Future<void> destroy() async {
    return;
  }
}
