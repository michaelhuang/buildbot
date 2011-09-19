#! /bin/sh

original=`echo $1 | sed 's|^./||'`

cat > $1 <<EOF
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>  
        <meta http-equiv="refresh" content="1;http://buildbot.net/buildbot/docs/current"/>

        <title>Buildbot Documentation (redirect)</title>
</head>

<body>
<p>This documentation has been moved to <a href="http://buildbot.net/buildbot/docs/current">buildbot.net</a>.  You will be redirected momentarily.</p>
</body>
</html>
EOF
