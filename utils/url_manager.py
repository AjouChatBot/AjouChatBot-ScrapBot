def adjust_url(url):
    
  # 탐색url 보정
  url_title_idx = url.find('#')

  if url_title_idx == -1:
      url_title_idx = len(url)

  return url[:url_title_idx]