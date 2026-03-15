# Use Apache HTTP Server base image
FROM httpd:2.4-alpine

RUN rm -rf /usr/local/apache2/htdocs/*

COPY *.html /usr/local/apache2/htdocs/

EXPOSE 80
