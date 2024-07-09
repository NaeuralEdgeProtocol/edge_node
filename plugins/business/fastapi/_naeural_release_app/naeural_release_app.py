from core.business.base.web_app import FastApiWebAppPlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,

  'ASSETS' : '_naeural_release_app',
  'JINJA_ARGS': {
    'html_files' : [
      {
        'name'  : 'releases.html',
        'route' : '/',
        'method' : 'get'
      }
    ]
  },
  'VALIDATION_RULES': {
    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}

class NaeuralReleaseAppPlugin(FastApiWebAppPlugin):

  CONFIG = _CONFIG

  def on_init(self, **kwargs):
    super(NaeuralReleaseAppPlugin, self).on_init(**kwargs)
    self._last_day_regenerated = (self.datetime.now() - self.timedelta(days=1)).day
    return

  def _regenerate_index_html(self):
    """
    Regenerate the index.html file.
    """

    # Fetch releases from the GitHub API
    url = "https://api.github.com/repos/NaeuralEdgeProtocol/edge_node_launcher/releases"
    response = self.requests.get(url)
    releases = response.json()

    # Sort releases by published date (descending order)
    releases.sort(key=lambda x: x['published_at'], reverse=True)

    # Define the HTML structure
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Edge Node Launcher Releases</title>
        <style>
            body {
                font-family: Arial, sans-serif;
            }
            .jumbo {
                background-color: #f8f9fa;
                padding: 2em;
                text-align: center;
            }
            .latest-release, .previous-releases {
                margin: 2em;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            table, th, td {
                border: 1px solid #ddd;
            }
            th, td {
                padding: 0.5em;
                text-align: left;
            }
        </style>
    </head>
    <body>
        <div class="jumbo">
            <h1>Edge Node Launcher Releases</h1>
            <p>Download the latest version of Edge Node Launcher to stay up-to-date with new features and improvements.</p>
            <button onclick="document.getElementById('latest-release').scrollIntoView();">Download Edge Node Launcher</button>
        </div>
    """

    # Add the latest release section
    latest_release = releases[0]
    latest_release_section = f"""
        <div class="latest-release" id="latest-release">
            <h2>Latest Release: {latest_release['tag_name']}</h2>
            <p>Date Published: {self.datetime.strptime(latest_release['published_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%B %d, %Y')}</p>
            <ul>
    """

    assets = latest_release['assets']
    for asset in assets:
        if self.re.search(r'LINUX_Ubuntu-20\.04\.zip', asset['name']):
            latest_release_section += f'<li>Linux Ubuntu 20.04: {asset["size"] / (1024 * 1024):.2f} MB - <a href="{asset["browser_download_url"]}">Download</a></li>'
        if self.re.search(r'LINUX_Ubuntu-22\.04\.zip', asset['name']):
            latest_release_section += f'<li>Linux Ubuntu 22.04: {asset["size"] / (1024 * 1024):.2f} MB - <a href="{asset["browser_download_url"]}">Download</a></li>'
        if self.re.search(r'WIN32\.zip', asset['name']):
            latest_release_section += f'<li>Windows: {asset["size"] / (1024 * 1024):.2f} MB - <a href="{asset["browser_download_url"]}">Download</a></li>'

    latest_release_section += f"""
                <li>Source Code: <a href="{latest_release['tarball_url']}">.tar</a>, <a href="{latest_release['zipball_url']}">.zip</a></li>
            </ul>
        </div>
    """

    html_content += latest_release_section

    # Add the previous releases section
    previous_releases_section = """
        <div class="previous-releases">
            <h2>Previous Releases</h2>
            <table>
                <thead>
                    <tr>
                        <th>Release Tag</th>
                        <th>Date</th>
                        <th>Linux</th>
                        <th>Windows</th>
                        <th>Source Code</th>
                    </tr>
                </thead>
                <tbody>
    """

    for release in releases[1:]:
        release_row = f"""
                    <tr>
                        <td>{release['tag_name']}</td>
                        <td>{self.datetime.strptime(release['published_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%B %d, %Y')}</td>
                        <td>
    """
        linux_20_04 = next((asset for asset in release['assets'] if self.re.search(r'LINUX_Ubuntu-20\.04\.zip', asset['name'])), None)
        linux_22_04 = next((asset for asset in release['assets'] if self.re.search(r'LINUX_Ubuntu-22\.04\.zip', asset['name'])), None)
        windows = next((asset for asset in release['assets'] if self.re.search(r'WIN32\.zip', asset['name'])), None)

        if linux_20_04:
            release_row += f'Ubuntu 20.04: {linux_20_04["size"] / (1024 * 1024):.2f} MB - <a href="{linux_20_04["browser_download_url"]}">Download</a><br>'
        if linux_22_04:
            release_row += f'Ubuntu 22.04: {linux_22_04["size"] / (1024 * 1024):.2f} MB - <a href="{linux_22_04["browser_download_url"]}">Download</a>'

        release_row += '</td><td>'

        if windows:
            release_row += f'{windows["size"] / (1024 * 1024):.2f} MB - <a href="{windows["browser_download_url"]}">Download</a>'

        release_row += f'</td><td><a href="{release["tarball_url"]}">.tar</a>, <a href="{release["zipball_url"]}">.zip</a></td></tr>'

        previous_releases_section += release_row

    previous_releases_section += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    html_content += previous_releases_section

    # Write the HTML content to a file
    self.P(self.get_assets_path())
    with open(self.os_path.join(self.get_assets_path(), 'assets/releases.html'), 'w') as file:
        file.write(html_content)

    print("releases.html has been generated successfully.")

    return

  def _maybe_regenerate_index_html(self):
    """
    Regenerate the html files if the last regeneration was more than X seconds ago
    ago.
    """
    current_day = self.datetime.now().day
    if current_day - self._last_day_regenerated >= 1:
      self._regenerate_index_html()
      self._last_day_regenerated = current_day
    
    return

  def process(self):
    self._maybe_regenerate_index_html()
    return
    