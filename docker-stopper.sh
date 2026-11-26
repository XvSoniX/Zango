for id in $(sudo docker ps -q); do
  if sudo docker update --restart=no "$id"; then
    pid=$(sudo docker inspect -f '{{.State.Pid}}' "$id")
    if [ "$pid" -gt 0 ] 2>/dev/null; then
      sudo kill -TERM "$pid"
    fi
  fi
done
