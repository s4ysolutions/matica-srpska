import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

import '../../bloc/matica_bloc.dart';

class SearchField extends StatelessWidget {
  const SearchField({super.key});

  @override
  Widget build(BuildContext context) {
    final searchBlock = context.read<MaticaBloc>();
    return TextField(
      decoration: InputDecoration(
        hintText: AppLocalizations.of(context)?.searchFieldHint,
        prefixIcon: const Icon(Icons.search),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      onChanged: (value) {
        print("onChanged: $value");
        searchBlock.add(MaticaSearchHeadwordPrefix(value));
      },
    );
  }
}
