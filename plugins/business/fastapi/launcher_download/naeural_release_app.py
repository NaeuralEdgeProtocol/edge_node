from core.business.default.web_app.fast_api_web_app import FastApiWebAppPlugin

__VER__ = '0.1.0.0'

_CONFIG = {
  **FastApiWebAppPlugin.CONFIG,

  'ASSETS' : 'plugins/business/fastapi/launcher_download',
  'JINJA_ARGS': {
    'html_files' : [
      {
        'name'  : 'releases.html',
        'route' : '/',
        'method' : 'get'
      }
    ]
  },
  'NR_PREVIOUS_RELEASES': 9,
  
  'REGENERATION_INTERVAL': 10*60, 
  
  "RELEASES_REPO_URL": "https://api.github.com/repos/NaeuralEdgeProtocol/edge_node_launcher",
  'VALIDATION_RULES': {

    **FastApiWebAppPlugin.CONFIG['VALIDATION_RULES'],
  },
}

class NaeuralReleaseAppPlugin(FastApiWebAppPlugin):

  CONFIG = _CONFIG

  def on_init(self, **kwargs):
    super(NaeuralReleaseAppPlugin, self).on_init(**kwargs)
    self._last_day_regenerated = (self.datetime.now() - self.timedelta(days=1)).day
    self.__last_generation_time = 0
    return

  # Fetch the latest 10 releases
  def get_latest_releases(self):
    releases_url = f"{self.cfg_releases_repo_url}/releases"
    response = self.requests.get(releases_url, params={"per_page": self.cfg_nr_previous_releases + 1})
    releases = response.json()
    return releases


  # Fetch the last 10 tags
  def get_latest_tags(self):
    tags_url = f"{self.cfg_releases_repo_url}/tags"
    response = self.requests.get(tags_url, params={"per_page": self.cfg_nr_previous_releases + 1})
    tags = response.json()
    return tags


  def get_commit_info(self, commit_sha):
    commit_url = f"{self.cfg_releases_repo_url}/commits/{commit_sha}"
    response = self.requests.get(commit_url)
    commit_info = response.json()
    return commit_info


  def compile_release_info(self, releases, tags):
    for release in releases:
      release_tag = release['tag_name'].strip("'")
      tag = next((tag for tag in tags if tag['name'].strip("'") == release_tag), None)

      if tag:
        commit_info = self.get_commit_info(tag['commit']['sha'])
        release['commit_info'] = commit_info
      else:
        release['commit_info'] = None
      # end if
    return releases


  def _regenerate_index_html(self):
    """
    Regenerate the index.html file.
    """

    releases = self.compile_release_info(self.get_latest_releases(), self.get_latest_tags())

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
    """ 
    last_update = self.datetime_to_str()
    html_content += f"""
    <body>
        <div class="jumbo">
            <h1>Edge Node Launcher Releases</h1>
            <p>Download the latest version of Edge Node Launcher to stay up-to-date with new features and improvements.</p>
            <p>This page was proudly generated by Edge Node <code>{self.ee_id}:{self.ee_addr}</code> at {last_update}.</p>
            <button onclick="document.getElementById('latest-release').scrollIntoView();">Download Edge Node Launcher</button>
        </div>
    """

    # Add the latest release section
    latest_release = releases[0]
    latest_release_section = f"""
        <div class="latest-release" id="latest-release">
            <h2>Latest Release: {latest_release['tag_name'].replace("'","")}</h2>
            <h3>Details:</h3>
            <div style="margin-left: 2em;">            
              <pre style="">{latest_release['commit_info']['commit']['message']}</pre>
            </div>
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
                        <th>Release Info</th>
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
                      <td>
                        {release['tag_name'].replace("'","")}
                        <div style="margin-left: 1em;">            
                          <pre style="">{release['commit_info']['commit']['message']}</pre>
                        </div>
                      </td>
                      
                      <td>
                        {self.datetime.strptime(release['published_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%B %d, %Y')}
                      </td>
                      
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
    # end for all releases

    previous_releases_section += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    html_content += previous_releases_section

    # Write the HTML content to a file
    self.P(self.get_web_server_path())
    with open(self.os_path.join(self.get_web_server_path(), 'assets/releases.html'), 'w') as fd:
      fd.write(html_content)

    self.P("releases.html has been generated successfully.")
    return


  def _maybe_regenerate_index_html(self):
    """
    Regenerate the html files if the last regeneration was more than X seconds ago
    ago.
    """
    current_day = self.datetime.now().day
    # if current_day != self._last_day_regenerated:
    if (self.time() - self.__last_generation_time) > self.cfg_regeneration_interval:
      self.P("Regenerating releases.html ...")
      self._regenerate_index_html()
      self._last_day_regenerated = current_day
      self.__last_generation_time = self.time()
    # end if
    return


  def process(self):
    self._maybe_regenerate_index_html()
    return
    