import datetime
import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from github import Auth, Github

# --- Configuration ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GH_USERNAME = os.getenv(
    "GH_USERNAME", "MushfiqPlabon"
)  # Default to user's GitHub username
OUTPUT_DIR = "assets"
MAX_COMMITS_TO_FETCH = 200  # Limit to avoid excessive API calls


def get_github_client():
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set.")
        # Fallback for local testing (rate-limited)
        return Github()
    auth = Auth.Token(GITHUB_TOKEN)
    return Github(auth=auth)


def fetch_user_data(g, username):
    user = g.get_user(username)
    print(f"Fetching data for user: {user.login}")

    repos = user.get_repos()
    print(f"Found {repos.totalCount} repositories.")

    all_commits = []
    # Fetch recent commits from owned repositories
    for repo in repos:
        if repo.fork:  # Skip forked repositories
            continue
        print(f"  Fetching commits for {repo.name}...")
        try:
            # Limit commits per repo to MAX_COMMITS_TO_FETCH / num_repos to stay within overall limit
            repo_commits = repo.get_commits(
                author=user.login,
                since=datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(days=365),
            )
            for i, commit in enumerate(repo_commits):
                if i >= MAX_COMMITS_TO_FETCH // 5:  # Arbitrary limit per repo
                    break
                all_commits.append(
                    {
                        "date": commit.commit.author.date,
                        "repo": repo.name,
                        "message": commit.commit.message,
                    }
                )
        except Exception as e:
            print(f"    Could not fetch commits for {repo.name}: {e}")

    # Sort commits by date
    all_commits.sort(key=lambda x: x["date"])
    print(f"Fetched {len(all_commits)} recent commits.")

    # Fetch language data
    language_data = {}
    for repo in repos:
        if repo.fork:
            continue
        try:
            langs = repo.get_languages()
            for lang, bytes_count in langs.items():
                language_data[lang] = language_data.get(lang, 0) + bytes_count
        except Exception as e:
            print(f"    Could not fetch languages for {repo.name}: {e}")

    total_bytes = sum(language_data.values())
    language_percentages = (
        {
            lang: (bytes_count / total_bytes) * 100
            for lang, bytes_count in language_data.items()
        }
        if total_bytes
        else {}
    )

    return {"user": user, "commits": all_commits, "languages": language_percentages}


def generate_commit_activity_chart(commits, output_path):
    if not commits:
        print("No commits to generate activity chart.")
        return

    dates = [c["date"] for c in commits]

    # Aggregate commits by day
    daily_commits = {}
    for date in dates:
        day = date.date()
        daily_commits[day] = daily_commits.get(day, 0) + 1

    sorted_days = sorted(daily_commits.keys())
    counts = [daily_commits[day] for day in sorted_days]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(sorted_days, counts, marker="o", linestyle="-")
    ax.set_title("Commit Activity (Last Year)", color="white")
    ax.set_xlabel("Date", color="white")
    ax.set_ylabel("Commits", color="white")
    ax.tick_params(axis="x", rotation=45, colors="white")
    ax.tick_params(axis="y", colors="white")
    ax.set_facecolor("#0d1117")  # GitHub dark theme background
    fig.patch.set_facecolor("#0d1117")  # Figure background

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.savefig(output_path, format="svg")
    print(f"Generated commit activity chart: {output_path}")


def generate_language_chart(languages, output_path):
    if not languages:
        print("No language data to generate chart.")
        return

    labels = languages.keys()
    sizes = languages.values()

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"color": "white"},
    )
    ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
    ax.set_title("Top Languages", color="white")
    ax.set_facecolor("#0d1117")  # GitHub dark theme background
    fig.patch.set_facecolor("#0d1117")  # Figure background

    plt.tight_layout()
    plt.savefig(output_path, format="svg")
    print(f"Generated language chart: {output_path}")


def generate_summary_text(data):
    summary = []
    summary.append("### Recent Activity Summary\n")
    summary.append(f"Hello, I'm {data['user'].name or data['user'].login}!\n")
    summary.append(
        f"In the last year, I've made {len(data['commits'])} commits across my public repositories.\n"
    )

    if data["languages"]:
        most_used_lang = max(data["languages"], key=data["languages"].get)
        summary.append(
            f"My most used language is **{most_used_lang}** ({data['languages'][most_used_lang]:.1f}%).\n"
        )

    summary.append("\n_This data is generated automatically via GitHub Actions._\n")
    return "\n".join(summary)


def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    g = get_github_client()
    user_data = fetch_user_data(g, GH_USERNAME)

    # Generate charts
    generate_commit_activity_chart(
        user_data["commits"], os.path.join(OUTPUT_DIR, "commit_activity.svg")
    )
    generate_language_chart(
        user_data["languages"], os.path.join(OUTPUT_DIR, "top_languages.svg")
    )

    # Generate summary text for README
    summary_text = generate_summary_text(user_data)

    # This part would write to a specific marker in README.md
    # For now, we'll just print it. The workflow will handle the README injection.
    print("\n--- Summary for README.md ---")
    print(summary_text)


if __name__ == "__main__":
    main()
