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

  @override
  Future<List<DictionaryEntry>> getEntriesByHeadwordBegin(
      String pattern) async {
    if (pattern.isEmpty) {
      return [];
    }
    final event =
        await _ref.orderByChild("headword").startAt(pattern).limitToFirst(10).once();
    final snapshot = event.snapshot;
    final results = <DictionaryEntry>[];
    if (snapshot.value != null) {
      final entries = Map<String, dynamic>.from(snapshot.value as Map);
      entries.forEach((key, value) {
        String headword = value["headword"];
        if (headword.startsWith(pattern)) {
          results.add(DictionaryEntry(headword: headword, definition: value["definition"]));
        }
      });
    }
    results.sort((a,b) => a.headword.compareTo(b.headword));
    return results;
  }

  @override
  Future<void> destroy() async {
    return;
  }
}
