import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:matica/services/matica.dart';

class MaticaChangeNotifier extends ChangeNotifier {
  late final StreamSubscription<MaticaSearchState>
      _maticaSearchStateSubscription;
  late final StreamSubscription<SearchResults> _maticaResultsSubscription;

  final MaticaService maticaService;

  MaticaChangeNotifier(this.maticaService) {
    _maticaSearchStateSubscription =
        maticaService.searchStateStream.listen((_) => notifyListeners);
    _maticaResultsSubscription =
        maticaService.searchResultsStream.listen((_) => notifyListeners);
  }

  void destroy() {
    _maticaSearchStateSubscription.cancel();
    _maticaResultsSubscription.cancel();
  }
}
