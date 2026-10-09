# Releasing the library

The source for each released skill lives under `skills/live/`, and skills still being finished live under `skills/in-progress/`. GitHub Releases holds the downloadable ZIPs. Keep the release tag, source commit, and package contents together so a download can be traced to its source.

## Add or update a skill

1. Add the complete package at `skills/live/<skill-name>/`, with `SKILL.md` at its root. The frontmatter's `name` must match the folder name, and it must include a `description`.
2. Include the references, assets, scripts, and other files the skill needs. Keep human-facing installation guides and examples under `docs/`, linked from the README.
3. Add or update its row in the [README catalog](../README.md#choose-a-skill), linking to its source and `https://github.com/GroundworkBusiness/groundwork-skills/releases/latest/download/<skill-name>.zip`.
4. Run the checks and build below. Review the skill and its complete ZIP before publishing.

The builder discovers every folder directly under `skills/live/` that contains `SKILL.md`. Adding a skill does not require changing the builder or maintaining a separate package list. The builder also checks the frontmatter and local Markdown links of skills under `skills/in-progress/`, but it does not package them, and the plugins do not load them.

This repository is the home for the public skill sources. When a skill is also distributed in a Groundwork plugin, use the same source folder to build that package. Document any required tools, companion skills, plugin components, or setup in the library documentation. A skill brought over from a plugin may depend on resources beyond its own folder; include or explain those dependencies before sharing it as an individual download.

## Move a skill from in progress to live

A skill under `skills/in-progress/` can be read and tried from the repository, but it has no ZIP and the plugins do not load it. To release it:

1. Finish the skill and check it against Anthropic's [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): a description that says what the skill does and when to use it, a `SKILL.md` body under 500 lines, references one level deep from `SKILL.md`, and at least three evaluations run on the models you support.
2. Move the folder with `git mv skills/in-progress/<skill-name> skills/live/<skill-name>`.
3. Move its row from the README's In progress table to the catalog, with its ZIP link.
4. Run the checks and build below, then publish a release that includes every current skill's ZIP.

## Build and check

Use the [maintainer environment](../README.md#environment):

```sh
uv sync --locked
uv run python scripts/build_packages.py --check
uv run python scripts/build_packages.py
```

The builder checks skill frontmatter and local Markdown file links. It then produces one complete ZIP per top-level skill, includes the MIT license in each, verifies the ZIP contents against the source, and writes `dist/SHA256SUMS`.

The output is repeatable: unchanged sources produce identical ZIPs. `dist/` and the local environment are ignored by Git.

## Publish

1. Review the source changes and the generated packages. Commit the final source.
2. Push the reviewed commit, then create a GitHub Release with a version tag pointing to that commit.
3. Attach every skill ZIP and `SHA256SUMS` from `dist/`. Publish the release as the latest stable release.
4. Download the published ZIPs and compare them with `SHA256SUMS`. Check the README's download links.

Include every current skill in each release. The README uses GitHub's `releases/latest/download/<skill-name>.zip` links, so an asset omitted from the newest release makes that skill's download link fail.

Keep version information on the release and tag, and keep ZIP filenames stable. GitHub's automatically generated source ZIP contains the entire repository; it is separate from the individual skill packages.

See [GitHub's release download documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases).

## Related

- [Library README](../README.md)
- [Installation overview](install/README.md)
