# Zero / Durable Zero — карта зависимостей, сборки и DI

**Текущий код, не проект будущей архитектуры.** Snapshot: PR #3 `85afe89869e60b887703d215005d4c37bac3c177`, проверенный remote head OPEN на 2026-11-06. Сам PR и код продукта не изменены; диаграммы опубликованы отдельной docs-веткой.

## Открыть карту

**[atlas.html](atlas.html)** — офлайн-атлас со всеми SVG, пояснениями и раскрываемым evidence для каждой точки подключения. Нет внешних скриптов, шрифтов и runtime dependencies. Сохранить директорию целиком и открыть HTML в браузере. Каждый SVG масштабируется без потери текста; клик по узлу/ячейке с evidence открывает исходник.

| Лист | Что показывает |
| --- | --- |
| [01 runtime.svg](runtime.svg) | Клиентский процесс, socket host, runner/Core, native Harness, models/tools, env/storage и обратные события |
| [02 public.svg](public.svg) | Реальные параметры и потребители: engine, две env factories, расширения, RPC streams/callback, UI source/controller/settings |
| [03 lower.svg](lower.svg) | ModelRuntime/providers, settings, resources, additional builtins, codemode, prompt options и dynamic sections: нижний API есть, верхний recipe не выставляет |
| [04 fixed.svg](fixed.svg) | Sandbox, coding-tools/subagents, MCP factory, discovery/prompt renderer, transport/UI choice; отдельно намеренные native owners Harness/SQLite |
| [05 dormant.svg](dormant.svg) | IModelProvider/PiAiModelProvider, ISessionStore/store adapter, host bridge, ISandboxExtension, full dispatcher и execution package — что не включено в штатный native recipe |
| [06 packages.svg](packages.svg) | Полная матрица зависимостей всех workspace-пакетов: source / type-only / manifest-only |
| [07 external.svg](external.svg) | Прямые source зависимости на Pi SDK, Zod, UI-библиотеки и Node built-ins; не транзитивный npm lock graph |

Mermaid companions для BB: `diagrams.json` и `*.mmd`. Там также есть sequence view `interaction.mmd`: `session/prompt` возвращает admission receipt, а результат native work приходит последующими событиями. Нельзя изображать RPC prompt как синхронный вызов, возвращающий весь ответ модели.

## Обозначения

- **G / зелёный:** явный параметр и реально найденный потребитель. Это оценка механизма подключения по исходникам, **не полный PASS продукта**. Уровень API указан: например, UI DI локальна в `runDurableTui`, а env factory доступна в программном `assembleDurableZero`, но не через CLI/socket RuntimeOptions.
- **Y / жёлтый:** существующий нижний native SPI. Реализацию передать можно при собственной сборке `PiDurableEngine/openDurable`; стандартная верхняя фабрика не выставляет такой слот.
- **R / красный:** конкретный выбор зашит в готовой сборке/bootstrap; отдельного параметра замены нет. Это ограничение заменяемости, не автоматическое объявление каждой такой строки багом.
- **D / серый:** есть код/контракт, но он не является активным заменяемым слотом штатного native startup. Самостоятельный helper может быть полезен и работоспособен вне этого recipe.
- **N / синий:** намеренный native owner. Сохранение одного Pi Harness и native storage — не требование вводить новый DI-контейнер или оборачивать каждую private SDK factory.

В package матрицах цвет не означает DI-status: **S** = source import/export/require/resolve; **T** = только type; **M** = объявлено в manifest без найденной source-ссылки. Синтаксический import не доказывает, что весь файл исполняется при конкретном startup. Тесты/dist исключены; публичные экспорты и vendor presentation source включены.

## Что важно увидеть в текущем состоянии

1. **Core → IAgentEngine действительно работает.** Coordinator вызывает `start/submit/events/abort/getState/.../close`; конкретный PiDurableEngine выбирает runner. Но injected generic engine не получает native `view/controller` из return branch этой фабрики, тогда как terminal host требует эти capabilities. Это ограничение конкретного готового host, не нарушение чистоты Core.
2. **Окружение выполнения — реальная сквозная DI.** Core и native factories идут в `ExecutionEnvs.getOrCreate`, результат использует native Harness. В исходниках `runner/test/native-env-seam.test.ts` есть native startup/file-effect probes; новый запуск этих native тестов в данном разборе не выполнялся. Core SPI уже SDK ExecutionEnv, поэтому успешная инъекция не обещает поддержку каждой расширенной native операции.
3. **ModelRuntime/resources/settings/builtins имеют нижние входы.** Проблема не в полном отсутствии DI: `PiRuntimeDependencies` уже содержит slots и они реально читаются. Проблема в том, что `assembleDurableZero` сам создаёт выбранные части и не открывает их как входы. `modelRuntime` здесь native Pi contract; существование Core `IModelProvider` не означает, что Harness использует именно его.
4. **Добавление расширения не равно замене builtin.** `extensions` реально загружаются и регистрируют tools/providers; но `coding-tools` и `subagents` сначала добавляются обязательно, а `BuiltinExtensionRegistry` отклоняет повторный id. Целый codemode можно выбрать нижним `builtins` recipe, но верхний runner создаёт свой. Sandbox внутри штатного adapter-codemode тоже создаётся жёстко.
5. **Не все пакеты участвуют в default path.** Например, runner объявляет adapter-pi-ai и execution в manifest, но native recipe использует ModelRuntime и NodeExecutionEnv напрямую из Pi SDK. extension-pi-resource source оборачивает native settings/loader; его manifest-зависимости на Core/adapter-pi-durable сами по себе не являются runtime wiring.
6. **Host bridge и store нельзя засчитывать по интерфейсу.** `dependencies.hostBridge` не имеет execution consumer; Core IHostBridge и placeholder native IHostBridge — разные типы. Standalone `PiDurableSessionStore` не владеет Harness в штатной сборке: native SQLite открывается отдельно. Подключать дополнительного владельца БД для «использования интерфейса» было бы неверно.
7. **Настройка — не всегда замена реализации.** `provider/model/thinking`, paths skills/AGENTS и subagent policy выбирают модель/контент/данные политики. Они не заменяют ModelRuntime, loader, prompt renderer или subagent implementation.

Подробности для каждого компонента: `bindings.json` и секция Evidence в HTML. Поля: существующий вход, выбранная реализация, реальный consumer, способ замены сегодня, ограничение, test-scope и цитируемые file:line.

## Почему именно так нарисовано

Проверены первоисточники, не подборка картинок:

- [C4 notation](https://c4model.com/diagrams/notation): отдельный title/scope, legend, подписанные направленные отношения, protocol для межпроцессного обмена; цвет не должен быть единственным объяснением.
- [C4 FAQ](https://c4model.com/faq): для SDK часто уместнее package/code views; полезнее несколько focused views, чем одна перегруженная схема.
- [arc42 §5](https://docs.arc42.org/section-5/): статическая структура модулей и зависимостей.
- [arc42 §6](https://docs.arc42.org/section-6/): runtime scenarios, startup и взаимодействия.

Поэтому импорты не смешаны с message flow. Самые подробные схемы подключения — направленные wiring boards, а полный статический граф показан матрицей без нечитаемых пересечений стрелок. Это собственное применение рекомендаций, не попытка объявить граф точной стандартной C4 нотацией.

## Проверка и воспроизводимость

- Исходники взяты через `git archive` exact SHA; грязный рабочий checkout и старые dist не использовались как источник диаграмм.
- Package graph извлечён TypeScript AST из `src/bin/vendor`. У `source/type/manifest-only` сохранены source references.
- Каждая DI-классификация вручную прослежена от входа до consumer или до отсутствия mount. В частности проверены все поля `PiRuntimeDependencies`.
- `verify-map.test.mjs` проверяет против исходников все evidence quotes/file:line, все workspace-пакеты, классификацию graph edges, покрытие native dependency fields и полноту HTML. Genuine JUnit: `map-verification.junit.xml`.
- SVG проверены XML parser; HTML открыт в Chrome, прочитан обратно и проверен screenshot. Это механическая/визуальная проверка атласа, не runtime acceptance всех замен.
- Код продукта, schema, package dependencies и PR head не изменялись. Не выполнялись реальные модели/MCP и не трогались пользовательские сессии. Не проводился новый independent-agent review.

```sh
SOURCE_ROOT=/absolute/path/to/exact-pr-source \
node --test --test-timeout 5000 \
  --test-reporter=junit \
  --test-reporter-destination=/tmp/map-verification.junit.xml \
  docs/arch-improvement/cycle-8/di-map/verify-map.test.mjs
```

`scan-packages.mjs`, `inventory.py`, `render-atlas.py` — генераторы evidence/диаграмм; `SOURCE_ROOT` и `OUTPUT_DIR` задаются извне. Для AST scanner нужен TypeScript из исследуемого проекта или `TYPESCRIPT_MODULE`. Они не исполняют runtime исследуемого продукта.

### Architecture verification — scope этого анализа

- Checked: AP-020 (направление Core/adapter/host), AP-073 (места выбора defaults), AP-074 (реальные explicit inputs против dormant placeholder/global legacy), AP-076 (consumer methods и различие интерфейса от реально работающей подмены).
- Residual risk: source trace не доказывает полную native совместимость произвольных replacements, reload/cancellation correctness или готовность PR к merge. Подтверждённый MCP startup blocker остаётся отдельным открытым дефектом.
- **Implementation verdict не выдаётся:** продукт не изменён; это диагностическая карта текущего состояния, не утверждённый план его переделки.
