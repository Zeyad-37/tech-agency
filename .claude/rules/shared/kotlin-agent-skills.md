# JetBrains Kotlin Agent Skills

The official JetBrains skill pack ([Kotlin/kotlin-agent-skills](https://github.com/Kotlin/kotlin-agent-skills)) is enabled for this repo as the `kotlin-agent-skills@Kotlin` plugin (registered in `.claude/settings.json`). These skills are authoritative, maintained guidance for Kotlin-specific tasks — when a task matches one, the agent MUST invoke the skill via the Skill tool BEFORE writing code, and follow its instructions over generic knowledge.

## When Each Skill Is Automatically Applicable

| Skill | Invoke when the task involves… | Primary agents |
|-------|-------------------------------|----------------|
| `kotlin-backend-jpa-entity-mapping` | Creating or reviewing JPA/Hibernate entities in Kotlin, diagnosing N+1 or `LazyInitializationException`, entity equality/identity, indexes and uniqueness constraints | @Forge |
| `kotlin-tooling-agp9-migration` | Upgrading to Android Gradle Plugin 9.0+, KMP+AGP build incompatibilities, `com.android.kotlin.multiplatform.library` | @Link, @Kai |
| `kotlin-tooling-cocoapods-spm-migration` | Migrating a KMP project from CocoaPods (`kotlin("native.cocoapods")`) to Swift Package Manager (`swiftPMDependencies` DSL) | @Link, @Swift |
| `kotlin-tooling-immutable-collections-0-5-x-migration` | Bumping `kotlinx.collections.immutable` to 0.5.x, KEEP-0459 renames (`add`→`adding`, etc.), deprecation warnings from that library | @Link, @Kai |
| `kotlin-tooling-java-to-kotlin` | Converting `.java` files to idiomatic Kotlin (framework-aware: Spring, Lombok, Hibernate, Jackson, Dagger/Hilt, JUnit, Mockito, …) | @Forge, @Kai |

## Rules

1. **Skill first, then standards.** When a task matches a row above, load that skill before implementing. Where the skill and this repo's coding standards both speak, the skill governs the mechanics of the migration/conversion; the repo standards govern project structure, layering, naming, and testing.
2. **Check for new skills.** JetBrains adds skills over time (naming: `kotlin-<category>-<name>`). If a Kotlin task feels like it might have a dedicated skill that isn't listed here, check the installed plugin's skill list before falling back to generic knowledge. When a new skill is adopted, add a row to the table above.
3. **Dependency upgrades.** `/dependency-upgrade` runs involving AGP, `kotlinx.collections.immutable`, or KMP iOS dependency management MUST route through the matching skill above.
4. **If the plugin is not installed** (fresh clone, plugin install declined), tell @Zeyad to accept the `kotlin-agent-skills@Kotlin` plugin prompt or run `claude plugin marketplace add Kotlin/kotlin-agent-skills && claude plugin install kotlin-agent-skills@Kotlin` — do not silently proceed without it on matching tasks.
