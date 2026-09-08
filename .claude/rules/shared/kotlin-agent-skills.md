# JetBrains Kotlin Agent Skills

The official JetBrains skill pack ([Kotlin/kotlin-agent-skills](https://github.com/Kotlin/kotlin-agent-skills)) is a separate marketplace plugin, `kotlin-agent-skills@Kotlin`. These skills are authoritative, maintained guidance for Kotlin-specific tasks — when a task matches one, the agent MUST invoke the skill via the Skill tool BEFORE writing code, and follow its instructions over generic knowledge.

**It is not installed for you.** The tech-agency repo's own `.claude/settings.json` registers the Kotlin marketplace and enables the plugin, but that registration is local to this repo — it does **not** propagate to anyone who installs tech-agency as a plugin. Every consumer project must install it itself. Before relying on any skill in the table below, confirm it is available (it appears in the session's skill list); if it is not, follow Rule 4.

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
4. **If the plugin is not installed** — which is the default for any project that has not installed it explicitly — do **not** silently proceed on a matching task. Stop and tell @Zeyad to run:

   ```bash
   claude plugin marketplace add Kotlin/kotlin-agent-skills
   claude plugin install kotlin-agent-skills@Kotlin
   ```

   If @Zeyad declines, say plainly that you are proceeding on generic Kotlin knowledge without the skill's framework-aware workflow, and note it in the PR description. Never claim to have followed a skill you could not load.
