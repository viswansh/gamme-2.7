setup
======

1. please run ./configure to setup the configuration for project
   this is a simple script prompting for your google storage access key

deploy/run
==========
locally:-
    dev_appserver.py gamme-2.7 -p <port>

remote appengine:-

    update-config:-
        change app.yaml and update 
        application:  <app-id>

    deploy:-
        appcfg.py updaste gamme-2.7
    

limitations
===========
1. As per the google limitation on cloud storage, files greater than 32 MB
   are not currently handled. There is a workaround by using files and reading
   less than 32 MB but is currently not implemented by this project.


ThirdParty
==========
1. Boto (2.2.1)  :- https://github.com/boto/boto
2. oauth:- ( package included in gsutil )

https://developers.google.com/storage/docs/gsutil

Note:- Don't use boto provided by gsutil, as it has a conflict with HTTPSConnection 
       class provided by google appengine. This is resolved in the above release

UnitTests
=========
run 'python tests_gamme.py'
