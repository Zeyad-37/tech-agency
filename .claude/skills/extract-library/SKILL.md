---
name: extract-library
description: "Extract a module from an app into a standalone, published KMP library — repo scaffold, package rename, Maven Central publishing (releases + snapshots), consumer swap, and the composite-build dev flow. Use when promoting in-repo code to its own library, publishing to Maven Central, or wiring an app to consume a library it used to vendor. Triggers: 'extract into a library', 'standalone lib', 'promote module to library', 'publish to maven central', 'open source this module'."
---

# Extract a Module into a Standalone Library

Proven end to end by `pagecurl-cmp` (vendored Steady module → `io.github.zeyad-37:pagecurl-cmp` on Maven Central, 2026-08). Owner: @Link for KMP libraries. Every step below was needed at least once; skipping the gotchas costs hours.

## Phase 0 — Scope the seam

Before any code moves, establish with the user:

- **What exactly is library-worthy?** The reusable engine, not the app's integration layer. (pagecurl: the pager/gesture/draw code went; Steady's `DateCurl` date-mapping stayed in the app. For a journal editor: the document model + editor engine go; the app's persistence and screens stay.)
- **Where are the platform seams?** Count the `expect`/`actual`s the extraction needs. If the module is `commonMain`-clean except for a few functions, the extraction is cheap — read the source before believing any "not multiplatform-compatible" claim.
- **Who consumes what?** List the app modules that will swap to the artifact, and which app-side tests pin the library's behavioral contract (these become the consumer regression gate after the swap).
- **License**: app code being open-sourced → owner's choice. A fork of third-party code → comply with the upstream license (Apache-2.0 derivatives may be MIT-relicensed if the upstream LICENSE + NOTICE are preserved; credit the original author prominently).

If the module isn't cleanly separable yet, vendor it first as an in-repo `:libs:<name>` module with its own package and iterate there — promote to a repo once stable (this is the pagecurl path: vendor → harden in production → extract).

## Phase 1 — Standalone repo

- Scaffold a fresh KMP repo: `:<lib>` library module + `sample/shared` (commonMain demo UI) + `sample/androidApp` + `sample/iosApp` (XcodeGen `project.yml`, committed `.xcodeproj`, `embedAndSignAppleFrameworkForXcode` script phase). AGP 9 KMP apps must split lib+app modules.
- **Copy the consumer app's version catalog values** (Kotlin, AGP, CMP, Gradle). AGP parity is not cosmetic — see the composite-build gotcha in Phase 4.
- **Rename the package to the owner's namespace** (e.g. `com.<owner>.<lib>`) so the artifact can never collide on a classpath with any upstream original.
- Port JVM-isms out of common code: `java.lang.Float.max` → `kotlin.math.max`, `Math.PI` → `kotlin.math.PI`, `System.currentTimeMillis()` → pointer-event `uptimeMillis`, `.java` class refs → discriminators.
- Move the app's unit tests for the extracted code into the repo's `commonTest`; add CI (`build.yml`, macos runner so iOS klibs compile).
- Info.plist for the iOS sample needs `CADisableMinimumFrameDurationOnPhone=true` (Compose-iOS crash-loops at launch without it).
- If the library renders UI: gate the extraction on a real-device performance check (simulators have desktop GPUs; a TestFlight internal build works even for a device that can't cable-pair).

## Phase 2 — Publishing pipeline (Maven Central Portal)

- vanniktech `com.vanniktech.maven.publish`; `gradle.properties`: `SONATYPE_HOST=CENTRAL_PORTAL`, `GROUP=io.github.<gh-user>`, `POM_ARTIFACT_ID`, `VERSION_NAME`, full POM fields.
- Make signing conditional on `signingInMemoryKey` presence so `publishToMavenLocal` works keyless — that's the local smoke test (verify all artifacts land in `~/.m2`).
- `publish.yml`: on tag `v*` → `./gradlew :<lib>:publishAndReleaseToMavenCentral --no-configuration-cache` (macos runner), env from 5 secrets: `MAVEN_CENTRAL_USERNAME`, `MAVEN_CENTRAL_PASSWORD`, `SIGNING_KEY`, `SIGNING_KEY_ID`, `SIGNING_KEY_PASSWORD`.
- `snapshot.yml`: on push to the main branch → compute next patch + `-SNAPSHOT` from `VERSION_NAME` → `publishToMavenCentral`. Snapshots land in minutes at `https://central.sonatype.com/repository/maven-snapshots/`.
- **Account steps only the user can do** (guide, never do for them): central.sonatype.com "Sign in with GitHub" (auto-verifies the `io.github.<user>` namespace), Generate User Token, run a local script that sets the repo secrets so tokens never transit the assistant.
- **Gotchas**: JitPack cannot build KMP (no macOS builders, no iOS klibs). Snapshot publishing 403s until SNAPSHOTs are enabled per namespace (namespace row → ⋯ → Enable SNAPSHOTs). A release's Gradle task returns in ~1 min but server-side PUBLISHING can take hours before repo1 sync (first release of a namespace is slowest); deployment state is visible only at central.sonatype.com/publishing/deployments. Public key must be on keyserver.ubuntu.com.

## Phase 3 — Swap the consumer app

Only after the artifact resolves from Central (or during the wait, verified against `mavenLocal()` as a rehearsal — temporarily, never committed):

1. Version catalog: add the artifact + version.
2. Replace every `implementation(projects.libs.<name>)` with the catalog accessor; delete the vendored module and its `settings.gradle.kts` include.
3. Keep (or add) app-side behavioral tests that pin the library semantics the app depends on — they are the regression gate for future version bumps.
4. Full verify: consumer host tests, Android assemble, iOS compile. Ship as a PR; from then on Renovate opens bump PRs automatically when new versions reach Central.

## Phase 4 — Dev flow for future changes

- **Inner loop**: gated composite build in the app's `settings.gradle.kts` —

  ```kotlin
  val libDev = providers.gradleProperty("<lib>.dev")
  if (libDev.isPresent) {
      includeBuild(libDev.get().ifEmpty { "../<lib>" }) {
          dependencySubstitution {
              substitute(module("io.github.<user>:<artifact>")).using(project(":<lib>"))
          }
      }
  }
  ```

  The explicit `dependencySubstitution` is required — KMP's multi-publication layout defeats Gradle's automatic substitution when project name ≠ artifactId. And **both builds must run the identical AGP version** or variant matching fails with "Could not determine whether value X is compatible with value Y using AgpVersionCompatibilityRule"; when the app bumps AGP, bump the library repo in the same breath.
- **Release flow**: PR on the lib repo → bump `VERSION_NAME` → tag → pipeline → Renovate bump PR in the app.
- **Urgent fixes while Central is slow**: consume the auto-published `-SNAPSHOT` by temporarily adding the snapshot repo (`mavenContent { snapshotsOnly() }`) on a branch.
- **Semver discipline**: app code often depends on library-internal *behavior* (not just API) — e.g. gesture/animation semantics. Changes there break consumers with zero compile errors: bump at least minor, write it in the release notes, and rerun the consumer's behavioral tests before the app upgrades.

Document Phases 2–4 in the library README (Snapshots + "Developing against an app" sections) so the flow survives context loss.
