# Composition API для Zero и Durable Zero

**Дата:** 2026-11-06. **Статус:** исследование и рекомендация, не утверждённый дизайн и не реализация. Код продукта, PR #3 и установленные рантаймы не изменялись.

## Короткий вывод

Рекомендую **контейнер-независимый API композиции с явными фабриками и модулями**, а не публичный `Container` в ядре Zero. Для текущих заменяемых частей Durable Zero начать с обычных фабрик: это полноценный Pure DI. Если независимым плагинам действительно понадобится автоматическое разрешение произвольного графа сервисов, использовать готовый resolver внутри сборочного слоя, а не писать свой универсальный DI-контейнер ради отсутствия npm-зависимостей. Это рекомендация по совокупности требований, а не утверждение о проверенной интеграции библиотеки с Harness. [S1][S2]

**Zero-dependency — средство, не смысл Zero.** Практичная цель: минимальные обязательные runtime-зависимости нейтрального ядра и отсутствие зависимости публичного plugin API от выбранного контейнера. Конкретная Durable-сборка вправе использовать полезные библиотеки. Важно различать отсутствие транзитивных зависимостей у библиотеки и отсутствие зависимости на саму библиотеку у Zero. Даже пакет без поля `dependencies` может приносить собственный большой семантический стек. [S3][S12]

## Контекст решения

- Разделение: общее headless/backendless ядро Zero и конкретная Pi Durable-backed реализация Durable Zero.
- Независимые плагины и замена одной части без форка остальных.
- Один native Harness остаётся владельцем model/tool/session execution. DI не должен вводить альтернативный execution loop.
- Есть async startup, собственные ресурсы, restart/reload и SQLite/session lease; одна сессия не должна получить двух одновременно активных владельцев.
- В исследованном PR #3 `85afe89869e60b887703d215005d4c37bac3c177` верхний `assembleDurableZero` принимает engine и execution-env factories, но не весь набор native model/resource/builtin dependencies. Нижний `PiRuntimeDependencies` уже имеет дополнительные слоты. Builtins `coding-tools`/`subagents` регистрируются до customBuiltins, повторный id отклоняется. [S14]

Это не полный аудит архитектуры. Исследование отвечает на выбор механизма композиции и его контрактов.

## Три подхода

### A. Типизированные recipes и фабрики — рекомендуемый старт

Пользователь передаёт реализации/фабрики в API сборки; стандартный Durable recipe объявляет готовый набор. Плагин экспортирует обычную фабрику или композиционный модуль с явными зависимостями. Не нужны reflection, decorators, classpath scanning или глобальный `resolve()`.

Это не означает, что пользователь вручную переписывает весь `main`: удобный API должен позволять заменить один слот и сохранить остальной рецепт. Не требуется автостроить произвольный граф неизвестных сервисов, если задача пока состоит в выборе известных engine/env/resources/builtins/extensions.

**Плюсы:** явные зависимости; ошибки типов в обычном TypeScript; небольшая обязательная поверхность; естественная интеграция с существующим Promise/native SDK. **Цена:** wiring остаётся кодом; по мере появления произвольных межплагинных зависимостей ручная сборка может стать неудобной. Pure DI — признанный подход, а не неполноценный контейнер. [S1][S2]

### B. Модули/providers + готовый resolver за адаптером

Имеет смысл, когда плагины не только заполняют известные слоты, но и создают новые сервисы, зависящие друг от друга. Тогда декларации `requires/provides`, проверка отсутствующих зависимостей, циклы, scope и автоматическая сборка дают реальную пользу.

Публичный контракт модулей должен принадлежать SDK, но **не нужно ради этого самостоятельно писать универсальный графовый resolver, систему scopes и lifecycle framework**. Сначала проверить, что произвольный граф действительно нужен, затем подобрать существующий механизм. Сам контейнер остаётся за границей application composition, не передаётся в Core и обычные бизнес-методы. Не стоит делать интерфейс, механически копирующий десятки методов выбранной библиотеки. [S2][S4][S5]

### C. Публичный API выбранного DI-контейнера

Плагины принимают конкретный `AwilixContainer`/`Container`/`Injector` и регистрируются напрямую. Быстро получить много возможностей, но типы, scopes, token identity, override/disposal semantics и обновления контейнера становятся частью совместимости плагинов.

**Для Zero не рекомендую как обязательный контракт.** Автор Composition Root отдельно предупреждает о сцеплении модулей с контейнером. Application, который встраивает Zero, должен сохранять свободу использовать собственный контейнер или Pure DI. [S2]

## Готовые библиотеки: что подтверждено

Версии и прямые runtime dependencies зафиксированы из npm registry; они не являются измерением размеров, скорости, качества или полной транзитивной цепочки. См. `package-snapshot.json`. [S3]

### Awilix — полезный обычный контейнер, но не async lifecycle framework

- Без обязательных специальных аннотаций; есть factories/classes/values, scoped/singleton/transient, strict mode и disposers. Документация предупреждает о захвате короткоживущих зависимостей долгоживущими. [S4]
- `CLASSIC` сопоставляет имена параметров с регистрациями; автор прямо предупреждает о minification. При использовании выбирать явные фабрики/объект зависимостей, не основывать SDK на именах JS-параметров. [S4]
- `dispose()` очищает собственный cache, но не закрывает автоматически дочерние scopes. В исходниках disposers запускаются через `Promise.all`: нельзя считать это гарантией последовательного teardown в обратном порядке зависимостей. [S4][S5]
- Поддержка async disposer не означает, что обычный `resolve()` разворачивает async factory в готовый объект для downstream factory. В исследованном коде используется непосредственное `resolver.resolve(...)`. Нужен явный async bootstrap/внешний lifecycle, а не предположение об автоматической готовности. [S5]

**Подходит:** необязательная внутренняя организация Durable-host, особенно уже созданных/синхронно создаваемых сервисов. **Не даёт автоматически:** plugin replacement policy, bounded cancellation startup, native lease policy и нужный порядок закрытия.

### typed-inject — действительно маленький и явный, но async acquisition — существенная оговорка

- Типизированные строковые токены и явные dependency tuples; документация показывает factories/classes без обязательных TS decorators/reflection. В опубликованном manifest нет runtime dependencies. [S3][S6]
- Есть child injectors, singleton/transient и async `dispose`. `provideValue` не означает владение переданным ресурсом. [S6]
- Но `provideFactory(async ...)` передаёт downstream-фабрике **Promise**, а не автоматически готовый ресурс. Отдельная async-factory enhancement issue остаётся открытой; код возвращает результат фабрики непосредственно. [S7][S8]
- Синтетические пробы именно опубликованного `typed-inject@5.0.0` подтвердили: Promise инъецируется как Promise; `dispose` объекта внутри него автоматически не вызывается; scope, созданный через `createChildInjector()`, в исследованном сценарии нужно явно закрыть, одного `root.dispose()` недостаточно. Это наблюдения конкретной версии и сценария, не заявление о всех способах использования библиотеки. [S9]

**Подходит:** явная синхронная сборка или выдача готовых значений. **Для текущего native async startup:** не выбирать, ожидая, что библиотека уже решает ожидание, rollback и cleanup acquisition. Это придётся делать отдельно. Ноль транзитивных dependencies сам по себе не делает её лучшим выбором.

### Inversify — кандидат, если нужен настоящий async dependency graph

- Официально описывает async bindings, ожидание зависимостей и `getAsync/getAllAsync`. `toResolvedValue` позволяет задавать фабрику и список зависимостей явно, поэтому неверно считать decorators обязательными для всех сценариев Inversify. [S10]
- Metadata-based constructor injection использует decorators/`emitDecoratorMetadata`; это отдельный режим, который не стоит навязывать всем Zero-плагинам. [S10]
- Request scope относится к одному container-resolution request, а не автоматически к RPC-запросу или агентной сессии. Async deactivation и binding lifecycle также требуют явной политики применения. [S10][S11]

**Подходит:** кандидат для отдельного spike при доказанной потребности в произвольном async-графе. **Не рекомендую:** вводить его публичные типы в нейтральный SDK только ради нескольких override-слотов. Интеграция с native Harness, аварийный startup rollback и cancellation в этом исследовании не тестировались.

### TSyringe — не первый выбор для этого SDK

Официальный путь настройки требует TS decorator metadata и Reflect polyfill; документация широко использует global container/side-effect registration. Существуют factory providers, child containers и disposal, но это не повод навязывать такой build/runtime contract plugin ecosystem. [S13]

**Вывод:** не рекомендую как стандарт Zero, учитывая явную инъекцию, ESM и запрет скрытого global state. Это не утверждение, что всякий проект с TSyringe неизбежно нарушает DIP.

### Effect Layers — содержательная альтернатива, но не просто DI-библиотека

Layer описывает output/error/input requirements и acquisition, Scope — lifetime/finalizers. В текущей v4-документации есть cleanup child scope при неудачном build и явные стратегии finalization. Это наиболее близкая концептуальная модель managed composition среди изученных вариантов. [S12]

Однако она приносит Effect-модель effects/context/scope и запуск через Effect runtime. Можно обернуть существующий native handle без замены его model loop; утверждать, что Layers обязательно требуют переписать Harness, было бы неверно. Но вводить этот семантический стек только ради DI в уже существующей native/Chord-системе сейчас не рекомендую. Manifest без внешних dependencies не равен отсутствию этого стека. [S3][S12]

### @tie-di/core — интересный экспериментальный кандидат, не default recommendation

README описывает явные typed tokens, modules, async factories, `resource(acquire/release)`, scoped ownership, reverse-order close, borrowed values и contributions. Manifest без runtime dependencies. Но автор прямо обозначает pre-1.0; опубликованная версия в snapshot — 0.2.0. [S3][S15]

По набору заявленных свойств очень близок к задаче. **Не отвергать заранее, но и не выбирать по README:** внутренний rollback/cancellation, SSR/ESM/plugin compatibility и native-интеграция не проверялись. Это кандидат для ограниченного сравнительного spike, не основание менять ядро сейчас.

## Best practices именно для этой сборки

Ниже — проектные рекомендации, выведенные из источников и текущих ограничений, а не универсальный стандарт языка.

1. **Разделить slot и collection.** Для engine/resources/env нужен один выбранный provider; для tools/extensions — коллекция с уникальными id. Не сводить обе модели к неявному last-wins. [S2][S14]
2. **Разделить add/replace/remove.** `replace` применяется к стандартному recipe до instantiation; ошибочный target/id и два конкурирующих overrides дают ошибку. Последний Registry по-прежнему отвергает неявные дубли. Замещённый builtin не должен успеть инициализироваться. Это наша рекомендуемая политика; контейнер не выберет её за продукт. [S14]
3. **Фабрики вместо повторного использования закрытых экземпляров.** Reload строит новое поколение owned components; нельзя после teardown случайно повторно выдать singleton старого поколения. Заимствованные внешние handles не закрывает тот, кто их не создавал. [S4][S6][S12]
4. **Один owner на ресурс.** Native Harness остаётся владельцем его внутренних сессий/SQLite/model/tool execution; outer assembly владеет своим native handle и внешними ресурсами, а не повторно закрывает внутренности SDK. Client disconnect не равен shutdown runtime. [S14]
5. **Минимально необходимые scopes.** Начать с assembly-generation lifetime и явно заимствованных ресурсов. Не добавлять process-global singleton или session/request scopes без конкретной потребности. Нельзя выдавать container resolution scope за lifetime сессии. [S4][S10]
6. **Pure validation до side effects; async acquisition и cleanup явно.** Структурные ошибки composition ловить до запуска engine. Ошибка создания одного компонента требует освободить уже приобретённые owned resources. Для последовательной сборки стандартный `AsyncDisposableStack` даёт LIFO async cleanup и продолжение при ошибке финализатора; доступность проверить по целевым host runtimes. В локальном Node 26.0.0 probe это подтверждено, но это не универсальная гарантия для всех потребителей SDK. [S9][S16]
7. **Timeout не равен cancellation.** Контейнер не отменит внешний HTTP/SDK startup сам. Нужна реальная поддержка abort/закрытия на стороне создаваемого ресурса; `Promise.race` с оставленной фоновой задачей не решает утечки. Optional/required policy и ready/degraded/failed — решение продукта. [S14]
8. **Reload с учётом lease.** Можно заранее подготовить/проверить чистый plan, но нельзя одновременно поднять два Harness на одной SQLite/session lease ради красивого blue-green switch. Нужны сериализация, quiescence, закрытие старого owner и запуск нового; возможный restart failure должен быть правдиво виден. Гарантию бесшовного rollback нельзя объявлять без отдельного native теста. [S14]
9. **Контейнер только в сборочном слое.** Core и плагины-потребители получают явные зависимости, не универсальный `getService`. Полезное различие — composition protocol, plugin lifecycle и runtime execution; они не обязаны реализовываться одной библиотекой. Fastify показывает самостоятельный plugin boot/lifecycle API, не требующий от каждого плагина публичного API конкретного DI-контейнера. [S2][S17]
10. **Совместимость независимых пакетов.** Явные ids/версии контрактов и runtime validation для динамически импортируемых модулей; TypeScript-проверка статического приложения не сертифицирует загруженный извне plugin. Не полагаться на равенство `Symbol()` из разных копий пакета и не лечить его скрытым global registry. Это рекомендация для отдельного дизайна plugin protocol, не готовая реализация в текущем PR.

## Какие реальные проверки нужны будущей реализации

- Плагин из отдельного fixture-пакета подключается через публичный API без правки исходников SDK.
- Custom builtin с id стандартного **реально исполняется** native Harness; стандартный не инициализируется и не исполняется.
- Remove/disable сохраняется после reload; новая generation создаёт новые owned instances.
- Внедрённый ресурс используется реальным путём prompting/tool execution, а не просто оказывается в возвращённом объекте.
- Ошибка второго acquisition и зависший startup дают правдивую ошибку; первая acquired resource закрывается; после cancellation нет owned survivors.
- Два runtime instance в одном процессе не делят изменяемое состояние.
- Закрытие client не закрывает runtime; shutdown закрывает каждого owner ровно один раз.
- Дубликаты и несуществующий override target отвергаются до побочных эффектов; дефолтная сборка продолжает native путь.

Это будущие acceptance criteria. Выполненные здесь четыре micro-probes **не являются** этими интеграционными проверками.

## Что проверено / чего не проверено

Прочитаны первоисточники: авторские статьи, официальные docs, README и исходники; npm manifest snapshots сохранены. Выполнены четыре изолированные синтетические пробы опубликованного typed-inject и стандартного JS cleanup; genuine JUnit рядом. npm archive проверен по опубликованному SHA-512 integrity; lifecycle scripts не запускались, библиотеки в проект и глобально не устанавливались. Нет реальных моделей, внешнего MCP или пользовательских сессий.

Awilix/Inversify/Effect/tie-di не проходили runtime integration spike; по ним выводы ограничены документацией/кодом. Не измерялись скорость, bundle size и operational reliability. Brain recall/query не завершились в ограниченных 7s попытках, поэтому не использованы как подтверждение; текущее решение опирается на диалог, зафиксированный код и первоисточники.

### Architecture verification — исследование, не implementation verdict

- Passed (recommendation-level): AP-020 — конкретная сборка снаружи нейтрального Core; AP-073 — defaults в recipe/bootstrap; AP-074 — явная инъекция, без глобального контейнера; AP-076 — критерии проверяют реальное использование dependency.
- Residual risk: окончательная поверхность module API, число свободно расширяемых слотов и библиотека resolver ещё не выбраны. Полная заменяемость, native reload и cancellation не доказаны этим исследованием. Не объявляется PASS продукта или готовность PR к merge.

## Повторить исследовательские пробы

Нужен распакованный или отдельно установленный `typed-inject@5.0.0`; зависимости рабочего проекта менять не нужно. Укажите директорию пакета, содержащую его `package.json`:

```sh
TYPED_INJECT_ROOT=/absolute/path/to/typed-inject \
node --test --test-timeout 3000 \
  --test-reporter=junit \
  --test-reporter-destination=/tmp/composition-probes.junit.xml \
  docs/arch-improvement/cycle-8/composition-api-research/container-semantics.test.mjs
```

Пробы исследуют наблюдаемую семантику, поэтому PASS здесь означает подтверждение описанных ограничений, а не отсутствие этих ограничений.

## Источники

- **S1:** Mark Seemann, [Pure DI](https://blog.ploeh.dk/2014/06/10/pure-di/).
- **S2:** Mark Seemann, [Composition Root](https://blog.ploeh.dk/2011/07/28/CompositionRoot/) — основной текст и ответы автора про module/container coupling.
- **S3:** npm registry manifests: [typed-inject](https://registry.npmjs.org/typed-inject/latest), [Awilix](https://registry.npmjs.org/awilix/latest), [Inversify](https://registry.npmjs.org/inversify/latest), [TSyringe](https://registry.npmjs.org/tsyringe/latest), [Effect](https://registry.npmjs.org/effect/latest), [tie-di](https://registry.npmjs.org/@tie-di%2fcore/latest); сохранённый version snapshot — `package-snapshot.json`.
- **S4:** [Awilix README](https://github.com/jeffijoe/awilix/blob/1daf3df5f935dadfb6c6b8de699b379c5b465053/README.md), sections lifetime/strict/injection/disposal.
- **S5:** [Awilix container source](https://github.com/jeffijoe/awilix/blob/1daf3df5f935dadfb6c6b8de699b379c5b465053/src/container.ts), `resolve`/`dispose`.
- **S6:** [typed-inject README](https://github.com/nicojs/typed-inject/blob/5d3c0276e65ade1d683239346488708b7a11e443/README.md).
- **S7:** [typed-inject implementation](https://github.com/nicojs/typed-inject/blob/5d3c0276e65ade1d683239346488708b7a11e443/src/InjectorImpl.ts).
- **S8:** [Async factories issue #30](https://github.com/nicojs/typed-inject/issues/30).
- **S9:** `container-semantics.test.mjs`, `container-semantics.junit.xml` — реальные локальные исследовательские пробы, не тесты интеграции Zero.
- **S10:** Inversify [Binding](https://inversify.io/docs/fundamentals/binding/) — async bindings, explicit factories, request scope.
- **S11:** Inversify [Container API](https://inversify.io/docs/api/container/).
- **S12:** Effect v4 [Layer](https://effect.website/docs/v4/api/effect/Layer), [Scope](https://effect.website/docs/v4/api/effect/Scope). Не смешивать с примерами v3 Context.Tag.
- **S13:** [TSyringe README](https://github.com/microsoft/tsyringe/blob/master/README.md).
- **S14:** PR #3 exact source: [composition.ts](https://github.com/VanDalkvist/durable-zero/blob/85afe89869e60b887703d215005d4c37bac3c177/packages/runner/src/composition.ts), [runtime-types.ts](https://github.com/VanDalkvist/durable-zero/blob/85afe89869e60b887703d215005d4c37bac3c177/packages/adapter-pi-durable/src/engine/runtime-types.ts), [harness-setup.ts](https://github.com/VanDalkvist/durable-zero/blob/85afe89869e60b887703d215005d4c37bac3c177/packages/adapter-pi-durable/src/engine/harness-setup.ts), [local-runtime](https://github.com/VanDalkvist/durable-zero/blob/85afe89869e60b887703d215005d4c37bac3c177/packages/local-runtime/src/index.ts), [подтверждённый MCP startup review](https://github.com/VanDalkvist/durable-zero/pull/3#issuecomment-6684195890).
- **S15:** tie-di pinned [README](https://github.com/valtyr/tie-di/blob/78e530439d26bdfac60294496581fb5217a0b2e5/README.md), [core reference](https://github.com/valtyr/tie-di/blob/78e530439d26bdfac60294496581fb5217a0b2e5/packages/core/README.md). Свойства, кроме manifest, на уровне заявлений автора, не полной проверки исходников/интеграции.
- **S16:** TC39 [Explicit Resource Management](https://github.com/tc39/proposal-explicit-resource-management) — AsyncDisposableStack; локальная доступность и cleanup проверены S9, статус Stage по старому README не используется как утверждение о текущем стандарте.
- **S17:** Fastify [Plugins](https://fastify.dev/docs/latest/Reference/Plugins/) — register, encapsulation, async boot/close API как дополнительный архитектурный пример.
