from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring


def process_rules_from_querystring(querystring):
    try:
        group_name_or_id = querystring.get('GroupName')[0]
    except:
        group_name_or_id = querystring.get('GroupId')[0]

    ip_protocol = querystring.get('IpPermissions.1.IpProtocol', [None])[0]
    from_port = querystring.get('IpPermissions.1.FromPort', [None])[0]
    to_port = querystring.get('IpPermissions.1.ToPort', [None])[0]
    ip_ranges = []
    for key, value in querystring.items():
        if 'IpPermissions.1.IpRanges' in key:
            ip_ranges.append(value[0])

    source_groups = []
    source_group_ids = []

    for key, value in querystring.items():
        if 'IpPermissions.1.Groups.1.GroupId' in key:
            source_group_ids.append(value[0])
        elif 'IpPermissions.1.Groups' in key:
            source_groups.append(value[0])

    return (group_name_or_id, ip_protocol, from_port, to_port, ip_ranges, source_groups, source_group_ids)


class SecurityGroups(BaseResponse):
    def authorize_security_group_egress(self):
        self.ec2_backend.authorize_security_group_egress(*process_rules_from_querystring(self.querystring))
        return AUTHORIZE_SECURITY_GROUP_EGRESS_RESPONSE

    def authorize_security_group_ingress(self):
        self.ec2_backend.authorize_security_group_ingress(*process_rules_from_querystring(self.querystring))
        return AUTHORIZE_SECURITY_GROUP_INGRESS_REPONSE

    def create_security_group(self):
        name = self.querystring.get('GroupName')[0]
        description = self.querystring.get('GroupDescription', [None])[0]
        vpc_id = self.querystring.get("VpcId", [None])[0]
        group = self.ec2_backend.create_security_group(name, description, vpc_id=vpc_id)
        template = self.response_template(CREATE_SECURITY_GROUP_RESPONSE)
        return template.render(group=group)

    def delete_security_group(self):
        # TODO this should raise an error if there are instances in the group. See http://docs.aws.amazon.com/AWSEC2/latest/APIReference/ApiReference-query-DeleteSecurityGroup.html

        name = self.querystring.get('GroupName')
        sg_id = self.querystring.get('GroupId')

        if name:
            self.ec2_backend.delete_security_group(name[0])
        elif sg_id:
            self.ec2_backend.delete_security_group(group_id=sg_id[0])

        return DELETE_GROUP_RESPONSE

    def describe_security_groups(self):
        groupnames = self._get_multi_param("GroupName")
        group_ids = self._get_multi_param("GroupId")
        filters = filters_from_querystring(self.querystring)

        groups = self.ec2_backend.describe_security_groups(
            group_ids=group_ids,
            groupnames=groupnames,
            filters=filters
        )

        template = self.response_template(DESCRIBE_SECURITY_GROUPS_RESPONSE)
        return template.render(groups=groups)

    def revoke_security_group_egress(self):
        success = self.ec2_backend.revoke_security_group_egress(*process_rules_from_querystring(self.querystring))
        if not success:
            return "Could not find a matching egress rule", dict(status=404)
        return REVOKE_SECURITY_GROUP_EGRESS_RESPONSE

    def revoke_security_group_ingress(self):
        self.ec2_backend.revoke_security_group_ingress(*process_rules_from_querystring(self.querystring))
        return REVOKE_SECURITY_GROUP_INGRESS_REPONSE


CREATE_SECURITY_GROUP_RESPONSE = """<CreateSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
   <groupId>{{ group.id }}</groupId>
</CreateSecurityGroupResponse>"""

DELETE_GROUP_RESPONSE = """<DeleteSecurityGroupResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DeleteSecurityGroupResponse>"""

DESCRIBE_SECURITY_GROUPS_RESPONSE = """<DescribeSecurityGroupsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <securityGroupInfo>
      {% for group in groups %}
          <item>
             <ownerId>111122223333</ownerId>
             <groupId>{{ group.id }}</groupId>
             <groupName>{{ group.name }}</groupName>
             <groupDescription>{{ group.description }}</groupDescription>
             {% if group.vpc_id %}
             <vpcId>{{ group.vpc_id }}</vpcId>
             {% endif %}
             <ipPermissions>
               {% for rule in group.ingress_rules %}
                    <item>
                       <ipProtocol>{{ rule.ip_protocol }}</ipProtocol>
                       <fromPort>{{ rule.from_port }}</fromPort>
                       <toPort>{{ rule.to_port }}</toPort>
                       <groups>
                          {% for source_group in rule.source_groups %}
                              <item>
                                 <userId>111122223333</userId>
                                 <groupId>{{ source_group.id }}</groupId>
                                 <groupName>{{ source_group.name }}</groupName>
                              </item>
                          {% endfor %}
                       </groups>
                       <ipRanges>
                          {% for ip_range in rule.ip_ranges %}
                              <item>
                                 <cidrIp>{{ ip_range }}</cidrIp>
                              </item>
                          {% endfor %}
                       </ipRanges>
                    </item>
                {% endfor %}
             </ipPermissions>
             <ipPermissionsEgress>
               {% for rule in group.egress_rules %}
                    <item>
                       <ipProtocol>{{ rule.ip_protocol }}</ipProtocol>
                       <fromPort>{{ rule.from_port }}</fromPort>
                       <toPort>{{ rule.to_port }}</toPort>
                       <groups>
                          {% for source_group in rule.source_groups %}
                              <item>
                                 <userId>111122223333</userId>
                                 <groupId>{{ source_group.id }}</groupId>
                                 <groupName>{{ source_group.name }}</groupName>
                              </item>
                          {% endfor %}
                       </groups>
                       <ipRanges>
                          {% for ip_range in rule.ip_ranges %}
                              <item>
                                 <cidrIp>{{ ip_range }}</cidrIp>
                              </item>
                          {% endfor %}
                       </ipRanges>
                    </item>
               {% endfor %}
             </ipPermissionsEgress>
             <tagSet>
               {% for tag in group.get_tags() %}
                 <item>
                   <resourceId>{{ tag.resource_id }}</resourceId>
                   <resourceType>{{ tag.resource_type }}</resourceType>
                   <key>{{ tag.key }}</key>
                   <value>{{ tag.value }}</value>
                 </item>
               {% endfor %}
             </tagSet>
          </item>
      {% endfor %}
   </securityGroupInfo>
</DescribeSecurityGroupsResponse>"""

AUTHORIZE_SECURITY_GROUP_INGRESS_REPONSE = """<AuthorizeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</AuthorizeSecurityGroupIngressResponse>"""

REVOKE_SECURITY_GROUP_INGRESS_REPONSE = """<RevokeSecurityGroupIngressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</RevokeSecurityGroupIngressResponse>"""

AUTHORIZE_SECURITY_GROUP_EGRESS_RESPONSE = """
<AuthorizeSecurityGroupEgressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
   <return>true</return>
</AuthorizeSecurityGroupEgressResponse>"""

REVOKE_SECURITY_GROUP_EGRESS_RESPONSE = """<RevokeSecurityGroupEgressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</RevokeSecurityGroupEgressResponse>"""
