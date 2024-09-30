import 'package:flutter/material.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
import 'package:provider/provider.dart';

import '../../../services/matica.dart';

class SearchField extends StatelessWidget {
  const SearchField({super.key});

  @override
  Widget build(BuildContext context) {
    final maticaService = Provider.of<MaticaService>(context);
    return TextField(
      decoration: InputDecoration(
        hintText: AppLocalizations.of(context)?.searchFieldHint,
        prefixIcon: const Icon(Icons.search),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      onChanged: (value) =>
          maticaService.setFilter(DictionaryPrefixFilter(value)).catchError(
        (e, s) {
          FlutterError.reportError(FlutterErrorDetails(
            exception: e,
            stack: s,
          ));
          return MaticaSearchResults.empty;
        },
      ),
    );
  }
}
