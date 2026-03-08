# Google auth URL

Fresh one-time URL. Use it immediately.

Scopes requested:
- Gmail: readonly
- Calendar: full
- Identity: openid, userinfo.email, userinfo.profile

```text
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=868173221591-8c4deusti4l5ngsed70kq7h7uqjcp6pm.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fgwmcp-auth-kamran.zocomputer.io%2Foauth2callback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+openid&state=2d347e611269eaed7285b5a978d1ec6a&code_challenge=VymlOVqD5l97nfmIGOqtmuD8ZbmZuoGKAAHevFzwCYc&code_challenge_method=S256&access_type=offline&prompt=consent
```

Expected redirect:

```text
https://gwmcp-auth-kamran.zocomputer.io/oauth2callback
```

Important:
- close any old auth tabs first
- use this URL only once
- use it right away
