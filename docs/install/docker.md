# Running as a Docker Image

There's also a [pre-built Docker Image](https://hub.docker.com/r/fmtr/amniotic) available, so you can run on a NAS or
home server etc. To run in container, use this command to map through sound devices, audio and config files:

=== "compose"
```yaml
--8<--
compose.example.yml    
--8<--
```

=== ".env"
```dotenv
--8<--
compose.example.env   
--8<--
```