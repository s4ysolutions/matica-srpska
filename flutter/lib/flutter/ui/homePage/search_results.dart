import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:matica/data_layer/dictionary.dart';
import 'package:matica/flutter/bloc/matica_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';


class SearchResultsField extends StatelessWidget {
  const SearchResultsField({super.key});

  @override
  Widget build(BuildContext context) {
    print("SearchResultsField build");
    return BlocBuilder<MaticaBloc, MaticaState> (
      builder: (context, state){
        print("MaticaBloc listener: state=$state, results=${state.results}");
        final l10n = AppLocalizations.of(context)!;
        return switch(state) {
          MaticaNotReady() => Center(child: Text(l10n.initializeDictionary)),
          MaticaReady() => SearchResultsList(entries: state.results),
          MaticaSearching() => Center(child: LinearProgressIndicator()),
          MaticaHasResults() => SearchResultsList(entries: state.results),
        };
      },
    );
  }
}

class SearchResultsList extends StatelessWidget {
  final List<DictionaryEntry> _entries;
  SearchResultsList({super.key, required List<DictionaryEntry> entries})
    : _entries = entries {
    print("SearchResultsList constructor: entries=$entries");
  }

  @override
  Widget build(BuildContext context) {
    print("SearchResultsList build: entries=$_entries");

    return ListView.builder(
      itemCount: _entries.length,
      itemBuilder: (context, index) {
        return ListTile(
          title: Text(_entries[index].headword),
          subtitle: Text(_entries[index].definition),
        );
      },
    );
  }
}
