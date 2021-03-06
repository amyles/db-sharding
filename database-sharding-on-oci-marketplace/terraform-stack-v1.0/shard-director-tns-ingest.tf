# Copyright 2020 Oracle Corporation and/or affiliates.  All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at http://oss.oracle.com/licenses/upl

resource "null_resource" "sdb_shard_director_tns_ingest" {
  depends_on = ["null_resource.sdb_shard_relay_tns_config", "null_resource.sdb_shard_director_aggregate_tns_config", "null_resource.sdb_shard_env_configure", "null_resource.sdb_shard_standby_configure", "null_resource.sdb_catalog_standby_configure", "null_resource.sdb_shard_director_install_main"]

  count = "${var.num_of_gsm}"

  triggers = {
    shard_db_ids              = "${join(",", oci_database_db_system.shard_db.*.id)}"
    shard_stdby_db_ips        = "${join(",", data.oci_core_vnic.shard_stby_db_node_vnic.*.public_ip_address)}"
    shard_catalog_standby_ips = "${join(",", data.oci_core_vnic.catalog_stby_db_node_vnic.*.public_ip_address)}"
  }

  #creates ssh connection to gsm host
  connection {
    type        = "ssh"
    user        = "${var.os_user}"
    private_key = "${tls_private_key.public_private_key_pair.private_key_pem}"
    host        = "${oci_core_instance.gsm_vm[count.index].public_ip}"
    agent       = false
    timeout     = "${var.ssh_timeout}"
  }

  provisioner "file" {
    content     = <<-EOF
      #! /bin/bash
      source ${var.oracle_base}/shard-director.sh
      cd ${var.oracle_base}
      echo "${tls_private_key.public_private_key_pair.private_key_pem}" > ikey-ingest
      chmod 600 ikey-ingest
      ${count.index == 0 ? "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ikey-ingest oracle@${oci_core_instance.gsm_vm[0].public_ip}:${var.oracle_base}/mesh-tnsnames ${var.oracle_base}/" : "Skipping TNS ingest for base shard director as it has been ingested already."}
      cat mesh-tnsnames >> $TNS_ADMIN/tnsnames.ora
      rm -f ikey-ingest
      EOF
    destination = "${var.oracle_base}/shard_director_tns_ingest.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod 700 ${var.oracle_base}/shard_director_tns_ingest.sh",
      "${var.oracle_base}/shard_director_tns_ingest.sh",
      "rm -f ${var.oracle_base}/shard_director_tns_ingest.sh"
    ]
  }
}