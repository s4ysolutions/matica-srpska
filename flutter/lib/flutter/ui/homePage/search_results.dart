import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:logger/logger.dart';
import 'package:matica/services/matica.dart';
import 'package:provider/provider.dart';

class SearchResultsField extends StatelessWidget {
  const SearchResultsField({super.key});

  @override
  Widget build(BuildContext context) {
    Logger logger = Provider.of<Logger>(context);
    logger.d("SearchResultsField build");
    return Consumer<MaticaSearchState>(
      builder: (context, state, _) {
        final l10n = AppLocalizations.of(context)!;
        return switch (state) {
          MaticaSearchState.uninitialized =>
            Center(child: Text(l10n.initializeDictionary)),
          MaticaSearchState.idle => SearchResultsList(),
          MaticaSearchState.searching =>
            Center(child: LinearProgressIndicator()),
          MaticaSearchState.error => SearchResultsList(),
        };
      },
    );
  }
}

class SearchResultsList extends StatelessWidget {
  const SearchResultsList({super.key});

  @override
  Widget build(BuildContext context) {
    Logger logger = Provider.of<Logger>(context);
    logger.d("SearchResultsList build");

    return Consumer<MaticaSearchResults>(
        builder: (context, results, _) => ListView.builder(
              itemCount: results.entries.length,
              itemBuilder: (context, index) {
                return ListTile(
                  title: Text(
                    results.entries[index].headword,
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(results.entries[index].definition),
                );
              },
            ));
  }
}
