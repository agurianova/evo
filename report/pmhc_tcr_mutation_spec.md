# Спецификация генотипа и операторов мутации
## pMHC–TCR recognition prediction (AlphaEvolve-style)

Версия 2. Исправляет пробелы аудита v1: явное состояние генотипа, precondition-функции,
числовые диапазоны, репарация после удаления входов, новые операторы, compute-aware fitness.

---

## 1. Генотип как явное состояние

Каждый потомок описывается JSON-объектом. Мутационные операторы читают и пишут в это
состояние, а не в "сырой код" напрямую — код генерируется из состояния детерминированным
компилятором. Это убирает главный источник невалидных программ: оператор может проверить
`is_applicable()` до применения.

```json
{
  "inputs": {
    "sequence": {"peptide": true, "mhc": true, "tcr_alpha": true, "tcr_beta": true},
    "pdb": {"present": false, "kind": null},          // kind: "complex" | "monomer" | null
    "masif": {"tcr_direct": false, "pmhc_flipped": false}
  },
  "encoders": {
    "sequence": {
      "region": "full",        // cdr1|cdr2|cdr3|all_cdr|fr1|fr2|fr3|fr4|all_fr|full
      "arch": "transformer",   // cnn|transformer|protein_lm
      "pretrained": false,     // см. правило 4.3
      "pooling": "mean",       // mean|attention
      "hidden_dim": 256
    },
    "structure": {
      "scope": "interface",    // full_complex|interface  (interface только если pdb.kind=="complex")
      "edges": {"type": "knn", "k": 16, "radius_A": null},
      "arch": "gat",           // gat|mpnn|egnn|se3_transformer
      "pooling": "mean",
      "hidden_dim": 256
    },
    "surface": {
      "patch_boundary": "nn_radius", // nn_radius|nn_learned
      "patch_radius_A": 12.0,
      "metrics": ["cosine", "dot", "l2", "max_sim", "mean_topk", "count_above_thr"],
      "topk": 10,
      "threshold": 0.7
    }
  },
  "interaction": {
    "pairs": [],              // subset of {peptide_tcr, peptide_mhc, mhc_tcr, peptide_mhc_tcr}
    "method": null,           // product|abs_diff|bilinear|cross_attention
    "fusion": null            // concat|gated_sum|cross_attention
  },
  "model": {
    "type": "mlp_features",   // mlp_features|seq_dual_encoder|seq_cross_encoder|pdb_gnn|
                               // masif_siamese|masif_patch_cross_attn|multimodal_mlp|
                               // multimodal_gated|multimodal_cross_attn|ensemble
    "hidden_dim": 256,
    "num_layers": 2,
    "num_heads": 4,
    "dropout": 0.1,
    "residual": true,
    "ensemble_members": []
  },
  "training": {
    "loss": "bce",            // bce|focal|contrastive
    "focal_gamma": 2.0,
    "sampling": "random",     // random|hard_negative
    "hard_negative_ratio": 0.3,
    "lr": 1e-3,
    "weight_decay": 1e-4,
    "optimizer": "adamw",     // adamw|adam|sgd   (новый, см. п.5.2)
    "scheduler": "none",      // none|cosine|step (новый, см. п.5.2)
    "batch_size": 64,         // новый, см. п.5.2
    "augmentation": {"seq_mask_p": 0.0, "structure_edge_dropout_p": 0.0} // новый, см. п.5.1
  },
  "calibration": {"temperature": 1.0},  // новый, см. п.5.3, не влияет на evaluator/метрики
  "seed": 0,
  "meta": {"generation": 0, "parent_id": null, "operator_applied": null}
}
```

Правило целостности: `interaction.pairs` может содержать `peptide_tcr` только если
`inputs.sequence.tcr_alpha or tcr_beta` истинно (или есть masif.tcr_direct / pdb с TCR-цепью
в комплексе), и т.д. — полная таблица в разделе 3.

---

## 2. Репарация и dead-code elimination

Проблема из аудита: `CHANGE_INPUT` может удалить модальность, от которой зависят
`interaction`, `encoders.surface`, ветки `model`. Так как на потомка разрешён ровно один
оператор, репарация не считается вторым оператором — это детерминированная постобработка.

**Алгоритм `repair(genotype)`, выполняется после любой мутации:**

1. Если `inputs.masif.tcr_direct == false` и `inputs.masif.pmhc_flipped == false` →
   обнулить `encoders.surface` (не используется, но не удаляется из истории — просто
   компилятор его не инстанцирует).
2. Пересчитать `interaction.pairs`: удалить пару, если хотя бы одна из требуемых модальностей
   отсутствует (см. таблицу применимости, раздел 3). Если список стал пустым — `interaction`
   отключается, `model.type` не может быть `multimodal_*`, откатывается на ближайший валидный
   тип (`mlp_features`, если остались хоть какие-то признаки, иначе — блокировка мутации целиком,
   см. п.6).
3. Если `inputs.pdb.kind != "complex"` → `encoders.structure.scope` принудительно `full_complex`
   → `interface` запрещён, межбелковые расстояния/грани между цепями удаляются из графа.
4. Если ни один энкодер не даёт эмбеддинг (все входы отсутствуют) — мутация **отклоняется целиком**,
   генотип-родитель возвращается без изменений, событие логируется как `invalid_mutation`
   (не расходует fitness-бюджет, но считается в статистике оператора для адаптивных весов, п.7).

Это заменяет неявное "два оператора за одного потомка" явным одним оператором + детерминированной
чисткой, которая не расширяет пространство поиска, а только поддерживает его валидность.

---

## 3. Таблица применимости (precondition) операторов

| Оператор | Precondition `is_applicable` | При провале |
|---|---|---|
| CHANGE_INPUT | всегда применим, кроме удаления последнего оставшегося входа | ресэмплировать другое действие (add вместо remove) |
| CHANGE_SEQUENCE | `inputs.sequence.*` есть хотя бы одна цепь; регион `cdr*/fr*` только для tcr_alpha/beta и mhc **не выбирается** (у MHC нет CDR/FR — см. п.4.1) | fallback на `full` |
| CHANGE_STRUCTURE | `inputs.pdb.present == true`; `scope=interface` доп. требует `inputs.pdb.kind=="complex"` | fallback `scope=full_complex` |
| CREATE_SURFACE | `inputs.masif.tcr_direct` и/или `inputs.masif.pmhc_flipped == true` | отклонить мутацию |
| CHANGE_INTERACTION | пара применима только если для **обеих** сторон пары существует хотя бы один энкодер (sequence/structure/surface), дающий эмбеддинг соответствующей молекулы | удалить недостижимые пары, п.2 |
| CHANGE_MODEL | `multimodal_*` требует ≥2 активных модальности; `ensemble` требует ≥2 валидных members | fallback на `mlp_features` или `seq_dual_encoder`, если есть sequence |
| CHANGE_TRAINING | всегда применим | — |

---

## 4. Разрешение неоднозначностей v1

### 4.1 CDR/FR только для TCR, не для MHC
`CHANGE_SEQUENCE.region` для `inputs.sequence.mhc` ограничен множеством
`{full, groove_a1a2, mask}` — MHC не имеет CDR/FR-разметки. Источник разметки:
локальная референсная база IMGT-нумерации для TCR alpha/beta (CDR1/2/3, FR1-4);
для MHC — доменная разметка α1/α2 (peptide-binding groove) / α3. При отсутствии записи
в локальной базе для конкретной последовательности — `region=full` + attention-mask
по неразмеченным позициям (как и было в v1, сохранено).

### 4.2 Числовые диапазоны (были не заданы — источник неограниченного/вырожденного поиска)

| Параметр | Диапазон | Дефолт |
|---|---|---|
| `structure.edges.k` (kNN) | 4–32, целое | 16 |
| `structure.edges.radius_A` | 4.0–15.0 Å | 8.0 |
| `surface.patch_radius_A` | 6.0–20.0 Å | 12.0 |
| `surface.topk` | 3–50 | 10 |
| `surface.threshold` (similarity) | 0.3–0.95 | 0.7 |
| `model.hidden_dim` | {64,128,256,512,768} | 256 |
| `model.num_layers` | 1–6 | 2 |
| `model.num_heads` | {1,2,4,8} (должно делить hidden_dim) | 4 |
| `model.dropout` | 0.0–0.5 | 0.1 |
| `training.lr` | 1e-5–1e-2 (log-uniform) | 1e-3 |
| `training.weight_decay` | 0–1e-2 (log-uniform, 0 допустим) | 1e-4 |
| `training.hard_negative_ratio` | 0.0–0.8 | 0.3 |
| `training.focal_gamma` | 0.5–5.0 | 2.0 |
| `training.batch_size` | {16,32,64,128,256} | 64 |

Любая мутация, меняющая непрерывный параметр, сэмплирует новое значение из указанного
диапазона (log-uniform там, где отмечено), а не произвольно — это закрывает "дорогу к
вырожденным графам" (`radius=0.1Å` и т.п.) из аудита.

### 4.3 Предобученные веса энкодера vs "запрещены внешние данные"
Разрешено использовать **фиксированные, задекларированные заранее** предобученные веса
protein LM (например, ESM-подобные), загруженные локально **до старта эволюции** —
это не "внешние данные" в смысле train/val/test labels или сетевых запросов во время
эволюции, а фиксированный артефакт окружения, одинаковый для всех потомков.
Ограничения:
- веса не дообучаются на val/test, не содержат сведений о разметке текущей задачи;
- список допустимых pretrained-чекпоинтов фиксирован в конфиге раннера, эволюция не может
  скачивать новые веса (сетевые запросы запрещены как и раньше);
- `encoders.sequence.pretrained=true` — фиксированный флаг, оператор `CHANGE_SEQUENCE`
  переключает `arch=protein_lm` вместе с этим флагом атомарно.

### 4.4 Разведение pooling по именованию
`encoders.sequence.pooling` и `encoders.structure.pooling` — раздельные поля (было неявно
пересекающееся в v1). Diff-логирование мутации всегда указывает, какое из двух полей
изменено.

### 4.5 dropout/residual — архитектура, не тренировка
Оставлены в `model.*` (CHANGE_MODEL), как архитектурные гиперпараметры. `training.*`
не содержит regularization-полей, кроме `weight_decay` (оптимизационный, не архитектурный).
Это разводит ответственность операторов 6 и 7 без пересечения.

---

## 5. Новые операторы (закрывают пробелы покрытия из аудита)

Нумерация продолжает исходный список; итого операторов 10.

### 5.1 CHANGE_AUGMENTATION
Изменить `training.augmentation`: `seq_mask_p` (0.0–0.3, вероятность маскирования
токена последовательности) или `structure_edge_dropout_p` (0.0–0.3, вероятность удаления
ребра графа). Действует **только на train**, не затрагивает preprocessing val/test.
Precondition: применим всегда; конкретное под-поле активно, только если соответствующий
энкодер присутствует в генотипе (иначе no-op, но операция всё равно валидна и логируется —
не расходуется впустую, т.к. может подготовить почву для будущего CHANGE_INPUT).

### 5.2 CHANGE_OPTIMIZATION
Изменить `training.optimizer` (adamw/adam/sgd), `training.scheduler` (none/cosine/step) или
`training.batch_size` (из дискретного набора п.4.2). Ровно одно из трёх меняется за вызов
оператора (сохраняем принцип "один аспект за мутацию" внутри самого оператора, аналогично
тому, как CHANGE_MODEL меняет один гиперпараметр).

### 5.3 CHANGE_CALIBRATION
Изменить `calibration.temperature` (0.5–3.0). Применяется **после** финального сигмоида,
не меняет ранжирование (значит не влияет на AUC/ranking-метрики), но меняет откалиброванную
вероятность. Явно разрешено: **не считается изменением evaluator/метрик**, т.к. это часть
самой программы (её выхода), а не механизма измерения.

### 5.4 NOOP
Тождественная мутация — потомок идентичен родителю (кроме `seed`, если включён re-seeding).
Нужен как контроль дрейфа популяции и для baseline-сравнения в отчётах. Выбирается с малым
фиксированным весом (см. раздел 7), не в основной ротации.

Итоговый список операторов: `CHANGE_INPUT, CHANGE_SEQUENCE, CHANGE_STRUCTURE, CREATE_SURFACE,
CHANGE_INTERACTION, CHANGE_MODEL, CHANGE_TRAINING, CHANGE_AUGMENTATION, CHANGE_OPTIMIZATION,
CHANGE_CALIBRATION` + служебный `NOOP`.

---

## 6. Обработка полного тупика мутации

Если после `repair()` генотип не имеет ни одного работающего энкодера (например,
`CHANGE_INPUT` убрал последний вход) — мутация не применяется, потомок = копия родителя,
событие = `invalid_mutation`. Правило "минимум один вход обязателен" из исходного оператора 1
теперь проверяется явно в `CHANGE_INPUT.is_applicable` **до** попытки удаления, а не постфактум.

---

## 7. Compute-aware отбор и веса операторов

### 7.1 Проблема скрытого смещения (из аудита)
Дорогие архитектуры (SE(3)-Transformer на full complex + attention pooling) систематически
убиваются таймаутом раннера при равном бюджете, что смещает отбор в пользу дешёвых операторов
независимо от их истинного качества.

### 7.2 Compute-aware fitness
Итоговый fitness потомка:

```
fitness_adj = fitness_raw - λ * max(0, compute_cost / compute_budget - 1)
```

где `compute_cost` — измеренное время обучения/инференса на валидации (val используется
только evaluator'ом как и раньше, метрика не меняется — штраф добавляется поверх,
не подменяет саму метрику), `compute_budget` — фиксированный лимит на всю популяцию,
`λ` — коэффициент штрафа (гиперпараметр раннера, не эволюционируемый геном). Потомки,
вышедшие за таймаут аппаратно (hard kill), получают `fitness_raw = 0` и не участвуют в
отборе, но событие логируется отдельно от `invalid_mutation` (это `timeout`, не невалидный
генотип).

### 7.3 Адаптивные веса выбора оператора
Вместо равномерного сэмплирования оператора — bandit-схема (например, UCB1 или
epsilon-greedy) по историческому приросту fitness на оператор, с расписанием по поколениям:

- **ранние поколения** (structural exploration): повышенный базовый вес у
  `CHANGE_INPUT, CHANGE_STRUCTURE, CHANGE_MODEL, CREATE_SURFACE`;
- **поздние поколения** (fine-tuning): повышенный вес у
  `CHANGE_TRAINING, CHANGE_OPTIMIZATION, CHANGE_AUGMENTATION, CHANGE_CALIBRATION`;
- `NOOP` — постоянный малый вес (например, 2-3%) на всех поколениях как контроль.

Веса пересчитываются раз в N поколений на основе среднего `Δfitness_adj` для каждого
оператора за последние M применений (M, N — конфигурируемые константы раннера, не часть
генотипа).

---

## 8. Неизменные ограничения (перенесены из v1 без изменений)

- Не изменять `labels`, `split`, `evaluator`, набор метрик.
- Preprocessing и negative sampling — только на train split.
- Запрещён доступ к val/test labels, внешним данным (кроме фиксированных pretrained весов,
  п.4.3) и сетевым запросам во время эволюции.
- Обязательный `seed`, соблюдение `compute_budget` (теперь формализовано в fitness, п.7.2).
- Enforcement предлагается через: (a) sandbox с read-only монтированием файлов
  labels/split/evaluator, (b) AST-whitelist разрешённых модулей/функций в
  сгенерированном коде, (c) автоматический diff сгенерированного кода против whitelist
  перед запуском — запуск блокируется при обнаружении обращения к запрещённым путям/API.

---

## 9. Итоговая сводка изменений относительно v1

| # | Проблема v1 | Исправление |
|---|---|---|
| 1 | Операторы независимы, но семантически связаны | Явный генотип-состояние + precondition-таблица (разд. 3) |
| 2 | Нет репарации после удаления входа | `repair()` + dead-code elimination (разд. 2) |
| 3 | Нет диапазонов гиперпараметров | Таблица диапазонов (разд. 4.2) |
| 4 | MHC ошибочно попадал под CDR/FR-логику | Явное разведение TCR/MHC регионов (разд. 4.1) |
| 5 | Конфликт pretrained LM vs "no external data" | Явное разрешение с ограничениями (разд. 4.3) |
| 6 | Пересечение pooling/dropout между операторами | Раздельные поля + фиксированная ответственность (разд. 4.4–4.5) |
| 7 | Нет augmentation/optimizer/calibration/noop | 4 новых оператора (разд. 5) |
| 8 | Дорогие архитектуры вымирают от таймаута | Compute-aware fitness (разд. 7.2) |
| 9 | Равномерный выбор оператора нестабилен | Adaptive bandit + расписание по поколениям (разд. 7.3) |
| 10 | Enforcement ограничений не специфицирован | Sandbox + AST-whitelist + pre-run diff (разд. 8) |

